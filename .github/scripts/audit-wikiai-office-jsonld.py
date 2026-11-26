#!/usr/bin/env python3
"""Verify public HFCM graphs; --sync mirrors only validated WordPress source."""
import argparse
import json
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

BASE = "https://www.wikiai.hu"
# Minimum size guards, not fixed historical node counts.
PAGES = {"/": 18, "/kapcsolat/": 15, "/rolunk/": 24, "/wikiai-hu/": 27}
MIRRORS = {
    "/wikiai-hu/": Path("wikiai/wikiai-hu.jsonld"),
    "/szakertok/": Path("wikiai/team.jsonld"),
    "/szakertok/simon-imre/": Path("wikiai/people/simon-imre.jsonld"),
    "/szakertok/varhelyi-csanad/": Path("wikiai/people/varhelyi-csanad.jsonld"),
}
PROFILE_NAMES = {
    "/szakertok/simon-imre/": "Simon Imre",
    "/szakertok/varhelyi-csanad/": "Várhelyi Csanád",
}
ORG = BASE + "/#organization"
PLACE = BASE + "/#editorial-office"
MAP = "https://www.openstreetmap.org/node/14303812090"
DIRECTORIES = {
    "https://aranyoldalak.hu/wikiai-hu.htm",
    "https://xn--hajdszoboszl-cib3g.cylex.hu/ceg-info/wikiai-hu-1317711.html",
}
FOUNDER = "https://www.wikiai.hu/szakertok/varhelyi-viktoria/#person"
LEGACY_FOUNDER = "https://www.varhelyicsanad.hu/varhelyi-viktoria.html#person"


class HeadJsonLd(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.head = False
        self.buffer = None
        self.docs = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.head = True
        if tag == "script" and self.head:
            attributes = dict(attrs)
            if attributes.get("type", "").strip().lower() == "application/ld+json":
                self.buffer = []

    def handle_data(self, data):
        if self.buffer is not None:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.buffer is not None:
            raw = "".join(self.buffer).strip()
            self.buffer = None
            try:
                doc = json.loads(raw)
                if isinstance(doc, list):
                    self.docs.extend(d for d in doc if isinstance(d, dict))
                elif isinstance(doc, dict):
                    self.docs.append(doc)
                else:
                    raise ValueError("JSON-LD root is not a document")
            except ValueError as exc:
                self.errors.append(str(exc))
        if tag == "head":
            self.head = False


def fetch(path):
    url = BASE + path + "?wikiai_schema_validation=" + str(time.time_ns())
    request = Request(url, headers={
        "User-Agent": "WikiAI-Official-JSONLD-Audit/1.0",
        "Accept": "text/html",
        "Cache-Control": "no-cache",
    })
    for attempt in range(4):
        try:
            with urlopen(request, timeout=38) as response:
                if response.status != 200:
                    raise RuntimeError("Unexpected HTTP status: " + str(response.status))
                location = urlsplit(response.geturl())
                if (location.scheme != "https" or location.netloc != "www.wikiai.hu"
                        or location.path != path):
                    raise RuntimeError("Unexpected redirect destination")
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise RuntimeError("HTML too large")
                if "html" not in response.headers.get("Content-Type", "").lower():
                    raise RuntimeError("Non-HTML response")
                return body.decode("utf-8")
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (URLError, TimeoutError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt + 1)
    raise RuntimeError("Cannot retrieve production HTML")


def read_head(path):
    parser = HeadJsonLd()
    parser.feed(fetch(path))
    if parser.errors:
        raise ValueError("Malformed JSON-LD in <head>: " + "; ".join(parser.errors[:3]))
    return parser.docs


def has_type(node, kind):
    types = node.get("@type", [])
    return kind in (types if isinstance(types, list) else [types])


def checked_graph(document, minimum):
    context = document.get("@context")
    contexts = context if isinstance(context, list) else [context]
    if not any(c in ("https://schema.org", "https://schema.org/") for c in contexts):
        raise ValueError("Missing Schema.org context")
    graph = document.get("@graph")
    if (not isinstance(graph, list) or len(graph) < minimum
            or any(not isinstance(n, dict) for n in graph)):
        raise ValueError("Invalid or suspiciously incomplete @graph")
    ids = [n["@id"] for n in graph if "@id" in n]
    if any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("Repeated or invalid @id in the same graph")
    return graph


def validate(path, minimum, mirrored_graph=None):
    candidates = []
    for doc in read_head(path):
        nodes = doc.get("@graph")
        if isinstance(nodes, list) and any(
            isinstance(n, dict) and n.get("@id") == PLACE for n in nodes
        ):
            candidates.append(doc)
    if len(candidates) != 1:
        raise ValueError("Expected exactly one editorial-office graph; found " + str(len(candidates)))
    document = candidates[0]
    graph = checked_graph(document, minimum)
    org = next((n for n in graph if n.get("@id") == ORG), None)
    place = next((n for n in graph if n.get("@id") == PLACE), None)
    if (not org or not place or not has_type(org, "Organization")
            or org.get("name") != "WikiAI.hu" or not has_type(place, "Place")):
        raise ValueError("Missing WikiAI Organization or Place")
    if org.get("telephone") != "+36702264545":
        raise ValueError("Organization telephone mismatch")
    founder_id = org.get("founder", {}).get("@id")
    if founder_id == LEGACY_FOUNDER:
        print("WARN", path, "uses retired founder Person ID; update the live WordPress/HFCM source to", FOUNDER, file=sys.stderr, flush=True)
    elif founder_id != FOUNDER:
        raise ValueError("Organization founder mismatch")
    if org.get("location") != {"@id": PLACE}:
        raise ValueError("Organization.location mismatch")
    if not DIRECTORIES.issubset(set(org.get("sameAs", []))):
        raise ValueError("Missing organization directory references")
    if place.get("hasMap") != MAP:
        raise ValueError("Place.hasMap mismatch")
    address = place.get("address", {})
    expected = {
        "streetAddress": "Déryné utca 3.",
        "postalCode": "4200",
        "addressLocality": "Hajdúszoboszló",
        "addressCountry": "HU",
    }
    if any(address.get(key) != value for key, value in expected.items()):
        raise ValueError("Editorial-office address mismatch")
    if path == "/wikiai-hu/" and mirrored_graph is not None and document != mirrored_graph:
        raise ValueError("Live HFCM organizational graph differs from GitHub JSON-LD mirror")
    print("PASS", path, len(graph), "nodes; live Place and Organization verified", flush=True)
    return document


def validate_directory_or_profile(path):
    canonical = BASE + path
    kind = "CollectionPage" if path == "/szakertok/" else "ProfilePage"
    minimum = 18 if kind == "CollectionPage" else (30 if path.endswith("/varhelyi-csanad/") else 4)
    candidates = []
    for document in read_head(path):
        graph = document.get("@graph")
        if not isinstance(graph, list):
            continue
        pages = [n for n in graph if isinstance(n, dict)
                 and has_type(n, kind) and n.get("url") == canonical
                 and n.get("@id") in (canonical, canonical + "#webpage")]
        if len(pages) == 1:
            candidates.append((document, pages[0]))
    if len(candidates) != 1:
        raise ValueError("Expected one canonical " + kind + "; found " + str(len(candidates)))
    document, page = candidates[0]
    graph = checked_graph(document, minimum)
    by_id = {n["@id"]: n for n in graph if "@id" in n}
    entity = page.get("mainEntity")
    if not isinstance(entity, dict) or not isinstance(entity.get("@id"), str):
        raise ValueError("Missing mainEntity identifier")
    if kind == "CollectionPage":
        main = by_id.get(entity["@id"], entity)
        org = by_id.get(ORG, {})
        if not has_type(main, "ItemList") or not main.get("itemListElement"):
            raise ValueError("Missing team ItemList")
        if not has_type(org, "Organization") or org.get("name") != "WikiAI.hu":
            raise ValueError("Incorrect team publisher")
    else:
        expected = canonical + "#person"
        person = entity if has_type(entity, "Person") else by_id.get(entity["@id"], {})
        if (entity["@id"] != expected or not has_type(person, "Person")
                or person.get("name") != PROFILE_NAMES[path]):
            raise ValueError("ProfilePage mainEntity Person identity mismatch")
        if path.endswith("/varhelyi-csanad/"):
            business = by_id.get(canonical + "#professional-service", {})
            org = by_id.get(ORG, {})
            if (not has_type(business, "Organization")
                    or business.get("duns") != "302346624"
                    or business.get("iso6523Code") != "0060:302346624"
                    or business.get("founder") != {"@id": expected}):
                raise ValueError("Independent professional-services identity or D-U-N-S mismatch")
            if not has_type(org, "Organization") or org.get("name") != "WikiAI.hu":
                raise ValueError("Incorrect WikiAI publisher identity")
            if person.get("url") not in (canonical, "https://www.varhelyicsanad.hu/"):
                raise ValueError("Unexpected professional reference URL")
    print("PASS", path, len(graph), "nodes;", kind, "and mainEntity verified", flush=True)
    return document


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--sync", action="store_true", help="Regenerate known mirrors from validated live HFCM graphs")
    sync = cli.parse_args(argv).sync
    failures = []
    documents = {}
    for path in list(PAGES) + [p for p in MIRRORS if p not in PAGES]:
        try:
            doc = (validate(path, PAGES[path]) if path in PAGES
                   else validate_directory_or_profile(path))
            if path in MIRRORS:
                target = MIRRORS[path]
                old = json.loads(target.read_text(encoding="utf-8"))
                if doc != old:
                    if not sync:
                        raise ValueError("Live HFCM graph differs from GitHub mirror: " + str(target))
                    documents[target] = doc
        except Exception as exc:
            failures.append(path + ": " + type(exc).__name__ + ": " + str(exc)[:240])
            print("FAIL", failures[-1], file=sys.stderr, flush=True)
    # Do not replace any snapshots until all live sources pass identity and graph checks.
    if not failures and sync:
        for target, doc in documents.items():
            target.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if json.loads(target.read_text(encoding="utf-8")) != doc:
                raise RuntimeError("Mirror read-back differs from verified source: " + str(target))
            print("MIRRORED", target, flush=True)
    print("Verified", len(set(PAGES) | set(MIRRORS)), "public WikiAI JSON-LD surfaces;",
          len(failures), "failures;", len(documents) if not failures else 0, "updated mirrors.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
