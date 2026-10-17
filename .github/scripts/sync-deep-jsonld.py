#!/usr/bin/env python3
"""Mirror validated live WikiAI HFCM deep JSON-LD to GitHub.

Preserve legacy, manually maintained *.jsonld files. Create a mirror for each
new business profile and update only files tracked by jsonld-sync-manifest.json.
WordPress remains the source of truth.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


MANIFEST = Path("manifest.json")
STATE_FILE = Path("jsonld-sync-manifest.json")
SOURCE_HOST = "www.wikiai.hu"
REQUIRED_SLUG = "porvadaszok-matractisztitas-debrecen"


def node_has_type(node, item):
    types = node.get("@type", [])
    return item in (types if isinstance(types, list) else [types])


class JsonLdScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reading = False
        self.chunks = []
        self.documents = []

    def handle_starttag(self, tag, attrs):
        if tag != "script":
            return
        attributes = dict(attrs)
        self.reading = attributes.get("type", "").lower() == "application/ld+json"
        self.chunks = []

    def handle_data(self, data):
        if self.reading:
            self.chunks.append(data)

    def handle_endtag(self, tag):
        if tag != "script" or not self.reading:
            return
        raw = "".join(self.chunks).strip()
        self.reading = False
        if not raw:
            return
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            return
        if isinstance(item, dict):
            self.documents.append(item)


def canonical_profile(entry):
    url = entry.get("canonical_url", "")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != SOURCE_HOST:
        raise ValueError("Unexpected WordPress host: " + url)
    if not parsed.path.endswith("/") or parsed.query or parsed.fragment:
        raise ValueError("Unexpected canonical URL: " + url)
    slug = parsed.path.strip("/")
    if not slug or not all(ch.isascii() and (ch.islower() or ch.isdigit() or ch == "-") for ch in slug):
        raise ValueError("Unexpected profile slug: " + slug)
    if entry.get("machine_record") != f"entities/{slug}.md":
        raise ValueError("Manifest path mismatch for " + slug)
    return url, slug


def download_html(url):
    req = Request(url, headers={
        "User-Agent": "WikiAI-JSONLD-Mirror/1.0 (+https://github.com/WikiAI-hu/wikiai-entities)",
        "Accept": "text/html",
        "Cache-Control": "no-cache",
    })
    with urlopen(req, timeout=22) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} at {url}")
        actual = urlsplit(response.geturl())
        if actual.netloc != SOURCE_HOST or actual.path != urlsplit(url).path:
            raise RuntimeError(f"Unexpected redirected URL: {response.geturl()}")
        data = response.read(4000001)
        if len(data) > 4000000:
            raise RuntimeError("HTML exceeds safe 4 MB limit")
        if b"<html" not in data[:8000].lower():
            raise RuntimeError("Expected rendered HTML")
        return data.decode("utf-8", "replace")


def graph_matches(document, canonical, slug):
    nodes = document.get("@graph")
    if document.get("@context") != "https://schema.org" or not isinstance(nodes, list) or len(nodes) < 12:
        return False
    ids = [n.get("@id") for n in nodes if isinstance(n, dict) and n.get("@id")]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) for i in ids):
        raise ValueError(f"Duplicate/invalid @id in {slug}")
    businesses = [
        n for n in nodes
        if isinstance(n, dict) and node_has_type(n, "LocalBusiness")
        and n.get("@id") == canonical + "#business"
    ]
    articles = [n for n in nodes if isinstance(n, dict) and node_has_type(n, "Article")]
    if len(businesses) != 1 or len(articles) != 1:
        return False
    main = articles[0].get("mainEntity")
    if not isinstance(main, dict) or main.get("@id") != canonical + "#business":
        return False
    if "mainEntityOfPage" in articles[0]:
        raise ValueError(f"Disallowed Article.mainEntityOfPage in {slug}")
    if not any(n.get("@id") == canonical + "#webpage" for n in nodes if isinstance(n, dict)):
        return False
    if articles[0].get("url") != canonical:
        return False
    return True


def find_deep_graph(html, canonical, slug):
    parser = JsonLdScripts()
    parser.feed(html)
    candidates = [doc for doc in parser.documents if graph_matches(doc, canonical, slug)]
    if len(candidates) != 1:
        raise ValueError(
            f"{slug}: expected one HFCM deep graph, got {len(candidates)}; "
            f"total JSON-LD scripts {len(parser.documents)}"
        )
    return candidates[0]


def digest(payload):
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--fixture-html", help="Offline test of the target profile only")
    opt = args.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = manifest.get("entities", [])
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("Empty/invalid manifest")
    state = (
        json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if STATE_FILE.exists() else
        {"schema_version": "1.0", "source_of_truth": "live WikiAI HFCM head", "managed": {}}
    )
    managed = state.get("managed")
    if not isinstance(managed, dict):
        raise RuntimeError("Invalid sync state")
    changed = 0
    seen_required = False
    for entry in entries:
        if entry.get("status") != "published":
            continue
        canonical, slug = canonical_profile(entry)
        if slug == REQUIRED_SLUG:
            seen_required = True
        dest = Path("entities") / f"{slug}.jsonld"
        is_managed = slug in managed
        if dest.exists() and not is_managed:
            print("PRESERVE manually maintained mirror:", dest)
            continue
        try:
            html = (
                Path(opt.fixture_html).read_text(encoding="utf-8")
                if opt.fixture_html and slug == REQUIRED_SLUG
                else download_html(canonical)
            )
            graph = find_deep_graph(html, canonical, slug)
            proposed = json.dumps(graph, ensure_ascii=False, indent=2) + "\n"
            existing = dest.read_text(encoding="utf-8") if dest.exists() else None
            if is_managed and existing and digest(existing) != managed[slug]["sha256"]:
                raise RuntimeError("GitHub mirror edited outside automation; refusing overwrite")
            if existing and json.loads(existing) == graph:
                print("UNCHANGED:", dest)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(proposed, encoding="utf-8")
            managed[slug] = {
                "file": dest.as_posix(),
                "source_url": canonical,
                "sha256": digest(proposed),
                "nodes": len(graph["@graph"]),
                "synced_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            changed += 1
            print("UPDATED:", dest, len(graph["@graph"]), "nodes")
        except Exception as exc:
            print("SYNC BLOCKED:", slug, type(exc).__name__, str(exc), file=sys.stderr)
            if slug == REQUIRED_SLUG or is_managed:
                raise
    if not seen_required:
        raise RuntimeError("Porvadaszok not found in the manifest")
    if changed:
        STATE_FILE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(f"Sync complete: {changed} changed; {len(managed)} managed mirror(s)")


if __name__ == "__main__":
    main()
