#!/usr/bin/env python3
"""Read-only check of WikiAI's actual, cache-busted production HTML JSON-LD."""
import json
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

BASE = "https://www.wikiai.hu"
PAGES = {"/": 30, "/kapcsolat/": 25, "/rolunk/": 41, "/wikiai-hu/": 46}
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
                if location.scheme != "https" or location.netloc != "www.wikiai.hu":
                    raise RuntimeError("Unexpected redirect destination")
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise RuntimeError("HTML too large")
                if "html" not in response.headers.get("Content-Type", "").lower():
                    raise RuntimeError("Non-HTML response")
                return body.decode("utf-8", "replace")
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (URLError, TimeoutError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt + 1)
    raise RuntimeError("Cannot retrieve production HTML")


def validate(path, count, mirrored_graph):
    parser = HeadJsonLd()
    parser.feed(fetch(path))
    if parser.errors:
        raise ValueError("Malformed JSON-LD in <head>: " + "; ".join(parser.errors[:3]))
    candidates = []
    for doc in parser.docs:
        nodes = doc.get("@graph")
        if isinstance(nodes, list) and any(
            isinstance(n, dict) and n.get("@id") == PLACE for n in nodes
        ):
            candidates.append(doc)
    if len(candidates) != 1:
        raise ValueError("Expected exactly one editorial-office graph; found " + str(len(candidates)))
    document = candidates[0]
    graph = document["@graph"]
    if len(graph) != count:
        raise ValueError("Expected " + str(count) + " nodes, found " + str(len(graph)))
    ids = [n["@id"] for n in graph if isinstance(n, dict) and n.get("@id")]
    if len(ids) != len(set(ids)):
        raise ValueError("Repeated @id in the same graph")
    org = next((n for n in graph if n.get("@id") == ORG), None)
    place = next((n for n in graph if n.get("@id") == PLACE), None)
    if not org or not place:
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
    if path == "/wikiai-hu/" and document != mirrored_graph:
        raise ValueError("Live HFCM organizational graph differs from GitHub JSON-LD mirror")
    print("PASS", path, count, "nodes; live Place and Organization verified", flush=True)


def main():
    mirror = json.loads(Path("wikiai/wikiai-hu.jsonld").read_text(encoding="utf-8"))
    failures = []
    for path, count in PAGES.items():
        try:
            validate(path, count, mirror)
        except Exception as exc:
            failures.append(path + ": " + type(exc).__name__ + ": " + str(exc)[:240])
            print("FAIL", failures[-1], file=sys.stderr, flush=True)
    print("Verified", len(PAGES), "public WikiAI JSON-LD surfaces;", len(failures), "failures.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
