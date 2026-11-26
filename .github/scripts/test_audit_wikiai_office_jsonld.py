"""Regression tests for the first-party HFCM mirror."""
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("official", Path(__file__).with_name("audit-wikiai-office-jsonld.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def html(doc):
    return '<html><head><script type="application/ld+json">' + json.dumps(doc) + '</script></head><body></body></html>'


def office_graph(count):
    nodes = [
        {"@type": "Organization", "@id": mod.ORG, "name": "WikiAI.hu",
         "telephone": "+36702264545", "founder": {"@id": mod.FOUNDER},
         "location": {"@id": mod.PLACE}, "sameAs": sorted(mod.DIRECTORIES)},
        {"@type": "Place", "@id": mod.PLACE, "hasMap": mod.MAP,
         "address": {"streetAddress": "Déryné utca 3.", "postalCode": "4200",
                     "addressLocality": "Hajdúszoboszló", "addressCountry": "HU"}},
    ]
    nodes.extend({"@type": "Thing", "@id": mod.BASE + "/#fixture-" + str(i)} for i in range(count - 2))
    return {"@context": "https://schema.org", "@graph": nodes}


def profile_graph():
    path = "/szakertok/varhelyi-csanad/"
    canonical = mod.BASE + path
    person = canonical + "#person"
    nodes = [
        {"@type": "ProfilePage", "@id": canonical, "url": canonical,
         "mainEntity": {"@type": "Person", "@id": person,
                        "name": "Várhelyi Csanád", "url": "https://www.varhelyicsanad.hu/"}},
        {"@type": "Organization", "@id": mod.ORG, "name": "WikiAI.hu"},
        {"@type": "Organization", "@id": canonical + "#professional-service",
         "founder": {"@id": person}, "duns": "302346624", "iso6523Code": "0060:302346624"},
    ]
    nodes.extend({"@type": "Thing", "@id": canonical + "#fixture-" + str(i)} for i in range(30))
    return {"@context": "https://schema.org", "@graph": nodes}


class OfficialMirrorTests(unittest.TestCase):
    def test_legitimate_node_growth_is_valid(self):
        graph = office_graph(31)
        with patch.object(mod, "fetch", return_value=html(graph)):
            self.assertEqual(mod.validate("/", mod.PAGES["/"]), graph)

    def test_identity_mismatch_still_fails(self):
        graph = office_graph(31)
        graph["@graph"][0]["founder"] = {"@id": "https://example.org/wrong"}
        with patch.object(mod, "fetch", return_value=html(graph)):
            with self.assertRaisesRegex(ValueError, "founder mismatch"):
                mod.validate("/", mod.PAGES["/"])

    def test_duplicate_id_rejected(self):
        graph = office_graph(31)
        graph["@graph"].append(graph["@graph"][0])
        with patch.object(mod, "fetch", return_value=html(graph)):
            with self.assertRaisesRegex(ValueError, "Repeated"):
                mod.validate("/", mod.PAGES["/"])

    def test_person_profile_and_duns(self):
        graph = profile_graph()
        path = "/szakertok/varhelyi-csanad/"
        with patch.object(mod, "fetch", return_value=html(graph)):
            self.assertEqual(mod.validate_directory_or_profile(path), graph)
        graph["@graph"][2]["duns"] = "000000000"
        with patch.object(mod, "fetch", return_value=html(graph)):
            with self.assertRaisesRegex(ValueError, "D-U-N-S"):
                mod.validate_directory_or_profile(path)


if __name__ == "__main__":
    unittest.main()
