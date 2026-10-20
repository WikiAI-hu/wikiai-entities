#!/usr/bin/env python3
"""Audited WordPress -> GitHub HFCM JSON-LD mirror for WikiAI business profiles.

The WordPress front-end is authoritative. This script intentionally does not
invent or modify Schema.org entities, WordPress/HFCM data, or historical sources.
It enrolls legacy mirrors only after comparing against a validated live graph.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifest.json"
STATE_FILE = ROOT / "jsonld-sync-manifest.json"
STATUS_FILE = ROOT / "jsonld-sync-status.json"
HOST = "www.wikiai.hu"
FIRST_PARTY_EXCEPTION = "https://www.wikiai.hu/wikiai-hu/"
MIN_DEEP_NODES = 10
MIN_PREVIOUS_NODE_RATIO = 0.60
MAX_HTML_BYTES = 4_000_000


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_if_changed(path, value):
    value = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != value:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        return True
    return False


def node_types(node):
    value = node.get("@type", [])
    return value if isinstance(value, list) else [value]


def ref_id(value):
    if isinstance(value, dict):
        return value.get("@id")
    if isinstance(value, str):
        return value
    return None


class HeadJsonLd(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.in_head = False
        self.current = None
        self.docs = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.in_head = True
        if tag == "script" and self.in_head:
            typ = dict(attrs).get("type", "")
            if typ.lower().strip() == "application/ld+json":
                self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            contents = "".join(self.current).strip()
            self.current = None
            if not contents:
                self.errors.append("Empty application/ld+json in head")
                return
            try:
                parsed = json.loads(contents)
                if not isinstance(parsed, (dict, list)):
                    raise ValueError("JSON-LD root must be an object or array")
                if isinstance(parsed, list):
                    self.docs.extend(x for x in parsed if isinstance(x, dict))
                else:
                    self.docs.append(parsed)
            except (ValueError, json.JSONDecodeError) as exc:
                self.errors.append("Invalid head JSON-LD: " + str(exc)[:180])
        if tag == "head":
            self.in_head = False


def parse_profile(entry):
    url = entry.get("canonical_url", "")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != HOST or parsed.query or parsed.fragment:
        raise ValueError("Invalid canonical domain or query: " + url)
    if not parsed.path.startswith("/") or not parsed.path.endswith("/"):
        raise ValueError("Canonical URL must have trailing slash: " + url)
    slug = parsed.path.strip("/")
    if not slug or "/" in slug or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in slug):
        raise ValueError("Invalid canonical slug: " + slug)
    if entry.get("machine_record") != "entities/" + slug + ".md":
        raise ValueError("Manifest Markdown path mismatch for " + slug)
    return url, slug


def download_html(canonical):
    # Cache-busting matters because HFCM changes need not invalidate WP page cache.
    query = "wikiai_jsonld_sync=" + str(int(time.time()))
    req = Request(canonical + "?" + query, headers={
        "User-Agent": "WikiAI-JSONLD-Mirror/2.0 (+https://github.com/WikiAI-hu/wikiai-entities)",
        "Accept": "text/html",
        "Cache-Control": "no-cache",
    })
    with urlopen(req, timeout=28) as response:
        if response.status != 200:
            raise RuntimeError("Unexpected HTTP status " + str(response.status))
        result = urlsplit(response.geturl())
        if result.scheme != "https" or result.netloc != HOST or result.path != urlsplit(canonical).path:
            raise RuntimeError("Unexpected redirect: " + response.geturl())
        ctype = response.headers.get("Content-Type", "")
        if "html" not in ctype.lower():
            raise RuntimeError("Expected HTML, got " + ctype)
        content = response.read(MAX_HTML_BYTES + 1)
        if len(content) > MAX_HTML_BYTES:
            raise RuntimeError("Rendered HTML exceeds 4 MB safety limit")
        html = content.decode("utf-8", "replace")
        if "<head" not in html[:100000].lower():
            raise RuntimeError("Rendered document has no head")
        return html


def expand_id(value, context):
    """Resolve custom prefixes declared in this JSON-LD graph, not by guessing IDs."""
    if not isinstance(value, str) or ":" not in value:
        return value
    prefix, remainder = value.split(":", 1)
    contexts = context if isinstance(context, list) else [context]
    for c in contexts:
        if isinstance(c, dict) and prefix in c:
            base = c[prefix]
            if isinstance(base, str):
                return base + remainder
            if isinstance(base, dict) and isinstance(base.get("@id"), str):
                return base["@id"] + remainder
    return value


def validate_graph(doc, canonical):
    graph = doc.get("@graph")
    context = doc.get("@context")
    def uses_schema(c):
        if isinstance(c, str):
            return c.rstrip("/") == "https://schema.org"
        if isinstance(c, list):
            return any(uses_schema(x) for x in c)
        if isinstance(c, dict):
            return uses_schema(c.get("@vocab"))
        return False
    if not uses_schema(context):
        return None
    if not isinstance(graph, list) or len(graph) < MIN_DEEP_NODES:
        return None
    if any(not isinstance(n, dict) for n in graph):
        return None
    articles = [n for n in graph if "Article" in node_types(n) and
                (n.get("url") == canonical or n.get("@id") == canonical + "#article" or
                 n.get("@id", "").endswith(":article"))]
    pages = [n for n in graph if "WebPage" in node_types(n) and
             n.get("url") == canonical]
    if len(articles) != 1 or len(pages) > 1:
        return None
    article = articles[0]
    if article.get("url", canonical) != canonical:
        return None
    warnings = []
    if len(pages) == 1:
        main_id = ref_id(article.get("mainEntity"))
        if not main_id or main_id != ref_id(pages[0].get("mainEntity")):
            return None
    else:
        # Historic Vargánya-style Article: no ProfilePage and the restaurant
        # is referenced via Article.about, with mainEntityOfPage a URL string.
        if article.get("mainEntityOfPage") != canonical:
            return None
        about = article.get("about", [])
        about = about if isinstance(about, list) else [about]
        referenced = {ref_id(x) for x in about}
        candidates = [n for n in graph if n.get("@id") in referenced
                      and n.get("name") and set(node_types(n)) &
                      {"Restaurant", "LocalBusiness", "Store", "Organization"}]
        if len(candidates) != 1:
            return None
        main_id = candidates[0]["@id"]
        warnings.append("Legacy Article without WebPage/mainEntity: business resolved from verified Article.about")
    business = [n for n in graph if n.get("@id") == main_id]
    if len(business) != 1 or not business[0].get("name"):
        return None
    if set(node_types(business[0])) & {"Article", "WebPage", "Person", "DigitalDocument"}:
        return None
    ids = [n["@id"] for n in graph if "@id" in n]
    if any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("Duplicate or invalid @id in deep graph")
    if not any(expand_id(n.get("@id"), context) == "https://www.wikiai.hu/#organization" for n in graph):
        return None
    # Schema.org permits an @id reference object for Article.mainEntityOfPage.
    main_page_ref = article.get("mainEntityOfPage")
    if isinstance(main_page_ref, dict) and not ref_id(main_page_ref):
        warnings.append("Article.mainEntityOfPage object lacks an @id")
    editor_id = "https://www.varhelyicsanad.hu/#person"
    for role in ("author", "editor", "accountablePerson"):
        # Publisher/editor/accountability fields are optional in Schema.org;
        # report incorrect explicit attribution, not merely absent optional fields.
        if role != "author" and article.get(role) is None:
            continue
        if expand_id(ref_id(article.get(role)), context) != editor_id:
            warnings.append("Article." + role + " does not reference Várhelyi Csanád")
    full = normalize_json(doc)
    slug = urlsplit(canonical).path.strip("/")
    if "entities/" + slug + ".md" not in full:
        warnings.append("Deep graph lacks a direct GitHub Markdown mirror reference")
    if "entities/" + slug + ".jsonld" not in full:
        warnings.append("Deep graph lacks a direct GitHub JSON-LD mirror reference")
    return {"doc": doc, "nodes": len(graph), "business_id": main_id,
            "business_name": business[0]["name"], "warnings": warnings}


def find_deep_graph(html, canonical):
    parser = HeadJsonLd()
    parser.feed(html)
    if parser.errors:
        raise ValueError("; ".join(parser.errors[:3]))
    matches = []
    for doc in parser.docs:
        result = validate_graph(doc, canonical)
        if result:
            matches.append(result)
    if len(matches) != 1:
        diagnostics = []
        for doc in parser.docs[:4]:
            ns = doc.get("@graph", [])
            if not isinstance(ns, list):
                diagnostics.append({"top_type": doc.get("@type"), "no_graph": True})
                continue
            article = next((n for n in ns if isinstance(n, dict) and "Article" in node_types(n)), {})
            page = next((n for n in ns if isinstance(n, dict) and "WebPage" in node_types(n)), {})
            diagnostics.append({
                "nodes": len(ns),
                "article_id": article.get("@id"),
                "article_url": article.get("url"),
                "article_main": ref_id(article.get("mainEntity")),
                "page_id": page.get("@id"),
                "page_url": page.get("url"),
                "page_main": ref_id(page.get("mainEntity")),
                "context": str(doc.get("@context"))[:160],
                "sample_nodes": [
                    {"type": n.get("@type"), "id": n.get("@id"), "url": n.get("url"),
                     "name": n.get("name"), "about": str(n.get("about"))[:120]}
                    for n in ns[:8] if isinstance(n, dict)
                ],
            })
        raise ValueError(
            f"Expected one valid HFCM deep graph in <head>, found {len(matches)} "
            f"of {len(parser.docs)} head JSON-LD documents; details: "
            + json.dumps(diagnostics, ensure_ascii=False, separators=(",", ":"))
        )
    return matches[0]


def prior_main_entity(graph, canonical):
    """Resolve both ordinary and historical Article.about business identities."""
    try:
        nodes = graph.get("@graph", [])
        articles = [n for n in nodes if "Article" in node_types(n) and
                    (n.get("url") == canonical or n.get("@id") == canonical + "#article" or
                     n.get("@id", "").endswith(":article"))]
        if len(articles) != 1:
            return None
        direct = ref_id(articles[0].get("mainEntity"))
        if direct:
            return direct
        about = articles[0].get("about", [])
        about = about if isinstance(about, list) else [about]
        ids = {ref_id(item) for item in about}
        named = [n for n in nodes if n.get("@id") in ids and n.get("name") and
                 set(node_types(n)) & {"Restaurant", "LocalBusiness", "Store", "Organization"}]
        return named[0]["@id"] if len(named) == 1 else None
    except (AttributeError, IndexError, TypeError):
        return None


def sync_entry(entry, managed, now, fixture=None):
    canonical, slug = parse_profile(entry)
    path = ROOT / "entities" / (slug + ".jsonld")
    state = managed.get(slug)
    if not (ROOT / "entities" / (slug + ".md")).is_file():
        raise RuntimeError("Markdown mirror missing from manifest: " + slug)
    html = fixture.read_text(encoding="utf-8") if fixture and fixture.exists() else download_html(canonical)
    result = find_deep_graph(html, canonical)
    graph, new_count = result["doc"], result["nodes"]
    proposed = json.dumps(graph, ensure_ascii=False, indent=2) + "\n"
    old_text = path.read_text(encoding="utf-8") if path.exists() else None
    old_graph = json.loads(old_text) if old_text is not None else None
    if state and old_text is None:
        raise RuntimeError("Managed mirror was deleted: " + slug)
    if state and sha256(old_text) != state.get("sha256"):
        raise RuntimeError("Managed mirror changed outside sync; refusing overwrite: " + slug)
    if old_graph is not None:
        old_count = len(old_graph.get("@graph", []))
        old_entity = prior_main_entity(old_graph, canonical)
        if old_entity and expand_id(old_entity, old_graph.get("@context")) != expand_id(result["business_id"], graph.get("@context")):
            old_business = next((n for n in old_graph.get("@graph", []) if n.get("@id") == old_entity), {})
            if not old_business.get("name") or old_business["name"].strip().casefold() != result["business_name"].strip().casefold():
                raise RuntimeError("Business identity changed without matching entity name; manual review needed: " + slug)
            if state is not None:
                raise RuntimeError("Managed business identity @id changed; manual review needed: " + slug)
            result["warnings"].append(
                "Legacy business @id changed from " + str(old_entity) + " to " +
                str(result["business_id"]) + "; verified same business name, source is live WordPress; review historic authority"
            )
        if old_count >= MIN_DEEP_NODES and new_count < max(MIN_DEEP_NODES, int(old_count * MIN_PREVIOUS_NODE_RATIO)):
            if state is not None:
                raise RuntimeError(f"Managed graph shrank unexpectedly ({old_count} -> {new_count} nodes): {slug}")
            result["warnings"].append(
                f"Legacy GitHub snapshot had {old_count} nodes, validated live HFCM has {new_count}; "
                "previous version remains in Git history"
            )
    different = old_graph != graph
    if different:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(proposed, encoding="utf-8")
    # The first successful legacy comparison enrolls old files for future HFCM edits.
    actual = path.read_text(encoding="utf-8")
    new_state = {
        "file": "entities/" + slug + ".jsonld",
        "source_url": canonical,
        "sha256": sha256(actual),
        "nodes": new_count,
        "synced_at_utc": now if different else (state or {}).get("synced_at_utc", now),
    }
    if state is None and old_text is not None:
        new_state["legacy_original_sha256"] = sha256(old_text)
    elif state and "legacy_original_sha256" in state:
        new_state["legacy_original_sha256"] = state["legacy_original_sha256"]
    managed[slug] = new_state
    return {
        "status": "ok",
        "source": canonical,
        "mirror": new_state["file"],
        "nodes": new_count,
        "warnings": result["warnings"],
        "change": "created" if old_text is None else "updated" if different else "adopted" if state is None else "unchanged",
    }


def run_sync(fixture_slug=None, fixture_path=None):
    manifest = json_file(MANIFEST)
    entries = manifest.get("entities", [])
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("Missing entities in WordPress GitHub manifest")
    state = json_file(STATE_FILE) if STATE_FILE.exists() else {}
    managed = state.setdefault("managed", {})
    state["schema_version"] = "2.0"
    state["source_of_truth"] = "WikiAI live HFCM JSON-LD in <head>"
    now = utc_now()
    statuses = {}
    processed = set()
    counts = {"total": 0, "ok": 0, "error": 0, "changed": 0, "warnings": 0, "excluded_first_party": 0}
    for entry in entries:
        if entry.get("status") != "published":
            continue
        canonical, slug = parse_profile(entry)
        if canonical == FIRST_PARTY_EXCEPTION:
            counts["excluded_first_party"] += 1
            continue
        if slug in processed:
            raise RuntimeError("Duplicate company slug in manifest: " + slug)
        processed.add(slug)
        counts["total"] += 1
        try:
            fixture = Path(fixture_path) if fixture_path and fixture_slug == slug else None
            result = sync_entry(entry, managed, now, fixture=fixture)
            statuses[slug] = result
            counts["ok"] += 1
            counts["changed"] += result["change"] in ("created", "updated", "adopted")
            counts["warnings"] += len(result["warnings"])
            print("OK", slug, result["change"], result["nodes"], "nodes", file=sys.stderr)
        except Exception as exc:
            counts["error"] += 1
            statuses[slug] = {"status": "error", "source": canonical, "message": str(exc)[:600]}
            print("ERROR", slug, type(exc).__name__, str(exc), file=sys.stderr)
    for slug in sorted(set(managed) - processed):
        counts["error"] += 1
        statuses[slug] = {
            "status": "error",
            "message": "Previously mirrored company removed from manifest; review before pruning public mirror",
        }
        print("ERROR", slug, "orphan mirror retained", file=sys.stderr)
    state_changed = save_if_changed(STATE_FILE, state)
    report_changed = save_if_changed(STATUS_FILE, {
        "schema_version": "1.0",
        "source_of_truth": "WordPress/HFCM live <head> JSON-LD",
        "policy": "Existing mirrors are enrolled after source validation; errors never overwrite good snapshots",
        "counts": {k: v for k, v in counts.items() if k not in ("changed",)},
        "profiles": {s: {k: v for k, v in d.items() if k != "change"} for s, d in sorted(statuses.items())},
    })
    print("SUMMARY", json.dumps(counts, ensure_ascii=False), "state_changed", state_changed,
          "report_changed", report_changed, file=sys.stderr)
    return counts


def check_status():
    r = json_file(STATUS_FILE)
    counts = r["counts"]
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    for slug, d in r["profiles"].items():
        if d["status"] != "ok":
            print("BLOCKED", slug, d.get("message"), file=sys.stderr)
        for msg in d.get("warnings", []):
            print("WARNING", slug, msg, file=sys.stderr)
    return 1 if counts.get("error", 0) else 0


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--check-status", action="store_true")
    args.add_argument("--fixture-slug", help="Test-only: use supplied HTML for one slug")
    args.add_argument("--fixture-html", help="Test-only: path to local rendered HTML")
    opt = args.parse_args()
    if opt.check_status:
        return check_status()
    run_sync(opt.fixture_slug, opt.fixture_html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
