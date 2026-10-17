#!/usr/bin/env python3
"""Mirror WikiAI's published organizational pages and expert profiles.

WordPress REST API = source of truth. Never invent people or re-add deleted pages.
Preserve hand-maintained JSON-LD; sync only Markdown, knowledge manifest and index.
"""

import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    from markdownify import markdownify
except ImportError:
    markdownify = None

ROOT = Path(__file__).resolve().parents[2]
HOST = "www.wikiai.hu"
BASE = "https://" + HOST
STATE = ROOT / "wikiai/knowledge-sync-state.json"
STATUS = ROOT / "wikiai/knowledge-sync-status.json"
KNOWLEDGE_MANIFEST = ROOT / "wikiai/manifest.json"
INDEX = ROOT / "wikiai/index.md"

# Fixed organizational pages; experts themselves are discovered dynamically.
CORE = [
    (101, "service_catalog", "wikiai/services.md", "szolgaltatasok"),
    (202, "pricing", "wikiai/pricing.md", "arak"),
    (21, "about", "wikiai/about.md", "rolunk"),
    (22, "team_directory", "wikiai/team.md", "szakertok"),
    (23, "contact", "wikiai/contact.md", "kapcsolat"),
]
ROLES = {143: "founder", 144: "cofounder"}
DOCS_MIN = 7
USER_AGENT = "WikiAI-Knowledge-Mirror/1.0 (+https://github.com/WikiAI-hu/wikiai-entities)"


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical(s):
    p = urlsplit(s)
    if p.scheme != "https" or p.netloc != HOST or p.query or p.fragment or not p.path.endswith("/"):
        raise ValueError("Invalid WordPress canonical URL: " + str(s))
    return s


def cleaned_title(raw):
    return html.unescape(re.sub(r"<[^>]+>", "", str(raw or ""))).strip()


def iso_gmt(value):
    if not value:
        raise ValueError("Missing WordPress modified_gmt")
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return date.astimezone(timezone.utc).isoformat(timespec="seconds")


def get_json(path, query):
    endpoint = BASE + "/wp-json/wp/v2/" + path + "?" + urlencode(query)
    error = None
    for attempt in range(3):
        try:
            req = Request(endpoint, headers={
                "Accept": "application/json",
                "Cache-Control": "no-cache",
                "User-Agent": USER_AGENT,
            })
            with urlopen(req, timeout=25) as response:
                if response.status != 200 or urlsplit(response.geturl()).netloc != HOST:
                    raise RuntimeError("Bad WordPress REST response for " + path)
                content = response.read(6_000_001)
                if len(content) > 6_000_000:
                    raise RuntimeError("REST response too large for " + path)
                result = json.loads(content.decode("utf-8"))
                if not isinstance(result, (dict, list)):
                    raise RuntimeError("Unexpected JSON root")
                return result
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError("WordPress REST unavailable: " + path + ": " + str(error))


def list_published_pages():
    pages = []
    p = 1
    while True:
        arr = get_json("pages", {
            "page": p,
            "per_page": 100,
            "status": "publish",
            "_fields": "id,link,title,slug,modified_gmt,status",
        })
        if not isinstance(arr, list):
            raise RuntimeError("WordPress pages inventory is not an array")
        pages += arr
        if len(arr) < 100:
            break
        p += 1
        if p > 25:
            raise RuntimeError("Unexpectedly large WordPress pages inventory")
    if len(pages) < DOCS_MIN:
        raise RuntimeError("Suspiciously incomplete WordPress published pages inventory")
    ids = [p.get("id") for p in pages]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate WordPress page IDs in inventory")
    return pages


def discover(pages):
    lookup = {p["id"]: p for p in pages}
    docs = []
    for post_id, document_type, path, slug in CORE:
        p = lookup.get(post_id)
        if not p or p.get("slug") != slug or p.get("status") != "publish":
            raise RuntimeError("Required WikiAI organizational page missing: #" + str(post_id))
        canonical(p["link"])
        docs.append((p, document_type, path, None))
    people = []
    for p in pages:
        url = canonical(p["link"])
        m = re.fullmatch(r"/szakertok/([a-z0-9-]+)/", urlsplit(url).path)
        if not m:
            continue
        slug = m.group(1)
        if p["id"] in (22,):
            continue
        if p.get("slug") != slug:
            raise RuntimeError("Profile slug differs from published URL: " + slug)
        title = cleaned_title(p.get("title", {}).get("rendered"))
        if not title or len(title) > 160:
            raise RuntimeError("Missing/inconsistent expert title for " + slug)
        role = ROLES.get(p["id"], "external_professional_partner")
        people.append((p, "person_profile", "wikiai/people/" + slug + ".md", role))
    if not people:
        raise RuntimeError("No published expert profiles found; refusing to empty the public roster")
    people.sort(key=lambda t: (0 if t[0]["id"] == 143 else 1 if t[0]["id"] == 144 else 2,
                               cleaned_title(t[0]["title"]["rendered"]).casefold()))
    return docs, people


def page_details(meta):
    value = get_json("pages/" + str(meta["id"]), {
        "_fields": "id,content,link,title,status,slug,modified_gmt",
    })
    if not isinstance(value, dict) or value.get("id") != meta["id"] or value.get("status") != "publish":
        raise RuntimeError("Page disappeared before content fetch: " + str(meta["id"]))
    if canonical(value.get("link")) != canonical(meta["link"]):
        raise RuntimeError("Page URL changed during read: " + str(meta["id"]))
    return value


def profile_role(record, body):
    role = record[3]
    if role in ("founder", "cofounder"):
        return role
    if re.search(r'data-entity-role=["\x27]external-professional-partner["\x27]', body, re.I):
        return "external_professional_partner"
    return "professional_profile"  # Do not invent employment or partnership.


def source_modified_from_md(content):
    m = re.search(r'^source_last_modified:\s*["\x27]?([^"\x27\n]+)', content, re.M)
    try:
        return iso_gmt(m.group(1).strip()) if m else None
    except (ValueError, TypeError):
        return None


def front_matter_value(value):
    return json.dumps(str(value), ensure_ascii=False)


def to_markdown(record, page, role, now):
    if markdownify is None:
        raise RuntimeError("markdownify Python package is required")
    p, doctype, relpath, _ = record
    raw = page.get("content", {}).get("rendered")
    if not isinstance(raw, str) or len(raw.strip()) < 150:
        raise RuntimeError("WordPress content is empty/truncated: " + relpath)
    source = canonical(page["link"])
    name = cleaned_title(page["title"]["rendered"])
    # Do not embed executable source scripts, editor styles or WP block comments.
    cleaned = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    cleaned = re.sub(r"<(script|style)\b[^>]*>.*?</\1\s*>", "", cleaned, flags=re.I | re.S)
    document = markdownify(cleaned, heading_style="ATX", bullets="-").strip()
    if len(document) < 200:
        raise RuntimeError("HTML-to-Markdown conversion too short: " + relpath)
    fields = [
        ("document_type", doctype), ("entity_name", name if doctype == "person_profile" else "WikiAI.hu"),
        ("language", "hu-HU"), ("status", "published"), ("canonical_url", source),
        ("source_post_id", page["id"]), ("source_of_truth", "wordpress"),
        ("sync_direction", "wordpress-to-github"),
        ("source_last_modified", iso_gmt(page["modified_gmt"])), ("synced_at", now),
    ]
    if doctype == "person_profile":
        fields.append(("relationship_to_wikiai", role))
    if doctype == "pricing":
        fields.append(("currency", "HUF"))
    head = ["---"] + [f"{key}: {int(value) if key == 'source_post_id' else front_matter_value(value)}"
                        for key, value in fields] + ["---", "", "# " + name, ""]
    return "\n".join(head) + document + "\n"


def make_person_entry(record, role):
    p, _, path, _ = record
    return {
        "document_type": "person_profile",
        "path": path,
        "canonical_url": canonical(p["link"]),
        "wordpress_post_id": p["id"],
        "name": cleaned_title(p["title"]["rendered"]),
        "relationship_to_wikiai": role,
    }


def make_document_entry(record, existing_docs):
    p, kind, path, _ = record
    old = next((x for x in existing_docs if x.get("path") == path), {})
    entry = {
        "document_type": kind, "path": path, "canonical_url": canonical(p["link"]),
        "wordpress_post_id": p["id"],
    }
    for key in ("currency", "valid_as_of"):
        if key in old:
            entry[key] = old[key]
    return entry


def update_manifest(docs, people, roles, now, manifest):
    output = dict(manifest)
    output["generator"] = "WikiAI GitHub Knowledge Mirror 1.0.0"
    output["source_of_truth"] = BASE + "/"
    output["sync_direction"] = "wordpress-to-github"
    output["documents"] = [make_document_entry(r, manifest.get("documents", [])) for r in docs]
    output["people"] = [make_person_entry(r, roles[r[0]["id"]]) for r in people]
    before = dict(manifest)
    before.pop("last_updated", None)
    compared = dict(output)
    compared.pop("last_updated", None)
    if before != compared:
        output["last_updated"] = now
    return output


def update_index(old, people):
    if not isinstance(old, str) or "\n## Szemelyek\n" not in old or "\n## Gepi index\n" not in old:
        raise RuntimeError("Unexpected knowledge index format; manual migration required")
    links = ["- [" + cleaned_title(p["title"]["rendered"]) + "](people/" +
             p["slug"] + ".md)" for p, _, _, _ in people]
    replacement = "\n## Szemelyek\n\n" + "\n".join(links) + "\n\n## Gepi index\n"
    return re.sub(r"\n## Szemelyek\n.*?\n## Gepi index\n",
                  lambda match: replacement, old, count=1, flags=re.S)


def main():
    pages = list_published_pages()
    docs, people = discover(pages)
    now = timestamp()
    previous = json.loads(KNOWLEDGE_MANIFEST.read_text(encoding="utf-8"))
    old_state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    managed = dict(old_state.get("managed", {}))
    pending = {}
    roles = {}
    changed = []
    unchanged = []
    for record in docs + people:
        metadata, doctype, rel, declared_role = record
        dest = ROOT / rel
        old = dest.read_text(encoding="utf-8") if dest.exists() else None
        if rel in managed and old is not None:
            import hashlib
            checksum = hashlib.sha256(old.encode("utf-8")).hexdigest()
            if checksum != managed[rel]:
                raise RuntimeError("Out-of-band change to a managed Markdown file: " + rel)
        current_mod = iso_gmt(metadata["modified_gmt"])
        needs_rendering = old is None or source_modified_from_md(old) != current_mod
        if needs_rendering:
            page = page_details(metadata)
            role = profile_role(record, page["content"]["rendered"]) if doctype == "person_profile" else None
            new = to_markdown(record, page, role, now)
            pending[dest] = new
            changed.append(rel)
        else:
            role = declared_role
            if doctype == "person_profile" and old is not None and metadata["id"] not in ROLES:
                old_role = re.search(r'^relationship_to_wikiai:\s*["\x27]?([^"\x27\n]+)', old, re.M)
                if old_role:
                    role = old_role.group(1).strip()
            unchanged.append(rel)
        if doctype == "person_profile":
            roles[metadata["id"]] = role
    manifest = update_manifest(docs, people, roles, now, previous)
    previous_index = INDEX.read_text(encoding="utf-8")
    new_index = update_index(previous_index, people)
    if manifest != previous:
        pending[KNOWLEDGE_MANIFEST] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        changed.append("wikiai/manifest.json")
    if new_index != previous_index:
        pending[INDEX] = new_index
        changed.append("wikiai/index.md")
    valid_paths = {r[2] for r in docs + people}
    known_orphans = sorted(rel for rel in managed if rel not in valid_paths)
    unmanaged_orphans = sorted(x.relative_to(ROOT).as_posix()
                               for x in (ROOT/"wikiai/people").glob("*.md")
                               if x.relative_to(ROOT).as_posix() not in valid_paths and
                               x.relative_to(ROOT).as_posix() not in known_orphans)
    # Confirm source checks before writing anything; no silent deletion.
    for target, body in pending.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    import hashlib
    for r in docs + people:
        rel = r[2]
        managed[rel] = hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
    # Unpublished/deleted profiles vanish from manifest + index. Old blobs are kept
    # in Git history, and stale managed .md is not deleted without a separate review.
    for old in known_orphans:
        managed.pop(old)
    state = {"schema_version": "1.0", "source": BASE + "/wp-json/wp/v2/pages",
             "managed": dict(sorted(managed.items()))}
    report = {
        "schema_version": "1.0",
        "ok": True,
        "published_core_documents": len(docs),
        "published_people": len(people),
        "published_wordpress_page_count": len(pages),
        "updated_paths": sorted(changed),
        "orphan_managed_markdown": known_orphans,
        "orphan_unmanaged_markdown": unmanaged_orphans,
        "indexed_people": [{"id": r[0]["id"], "name": cleaned_title(r[0]["title"]["rendered"]),
                            "path": r[2], "role": roles[r[0]["id"]]} for r in people],
        "policy": "All people from published WordPress profile pages; nonexistent/unpublished pages never appear in manifest",
    }
    for path, obj in ((STATE, state), (STATUS, report)):
        body = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
        if not path.exists() or path.read_text(encoding="utf-8") != body:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
    print(json.dumps({
        "published_core": len(docs), "published_people": len(people),
        "names": [cleaned_title(r[0]["title"]["rendered"]) for r in people],
        "modified": changed, "orphan_managed": known_orphans,
        "orphan_unmanaged": unmanaged_orphans,
    }, ensure_ascii=False, indent=2))
    if known_orphans or unmanaged_orphans:
        print("WARNING: orphan Markdown files need review; manifests already exclude them", file=sys.stderr)


if __name__ == "__main__":
    main()
