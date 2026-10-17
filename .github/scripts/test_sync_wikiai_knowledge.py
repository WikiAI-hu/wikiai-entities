"""Regression tests for WikiAI's dynamic knowledge mirror."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("sync-wikiai-knowledge.py")
spec = importlib.util.spec_from_file_location("wikiai_knowledge", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def page(post_id, slug, title, url=None, modified="2026-10-17T08:00:00"):
    return {
        "id": post_id, "slug": slug, "status": "publish",
        "link": url or ("https://www.wikiai.hu/" + (("szakertok/" if post_id in (143,144,1334) else "") + slug) + "/"),
        "title": {"rendered": title}, "modified_gmt": modified,
    }


def pages():
    p = [
        page(101,"szolgaltatasok","Szolgáltatások"),
        page(202,"arak","Árak"),
        page(21,"rolunk","Rólunk"),
        page(22,"szakertok","Munkatársaink"),
        page(23,"kapcsolat","Kapcsolat"),
        page(143,"varhelyi-csanad","Várhelyi Csanád"),
        page(144,"varhelyi-viktoria","Várhelyi Viktória"),
        page(1334,"simon-imre","Simon Imre"),
    ]
    return p


def fixtures(root):
    (root/"wikiai/people").mkdir(parents=True)
    for p, _, rel, _ in mod.discover(pages())[0] + mod.discover(pages())[1]:
        (root/rel).parent.mkdir(parents=True,exist_ok=True)
        (root/rel).write_text(
            '---\nsource_last_modified: "2026-10-17T08:00:00+00:00"\n---\n# ' +
            p["title"]["rendered"] + '\n\n' + ("x" * 300),encoding="utf-8")
    (root/"wikiai/manifest.json").write_text(json.dumps({
        "schema_version":"1.0", "generator":"WikiAI GitHub Knowledge Sync 0.1.3",
        "last_updated":"2026-10-16T00:00:00Z",
        "documents":[], "people":[{
            "document_type":"person_profile","name":"Molnár András",
            "path":"wikiai/people/molnar-andras.md","canonical_url":"https://www.wikiai.hu/szakertok/molnar-andras/",
            "wordpress_post_id":145,
        }],
    },ensure_ascii=False),encoding="utf-8")
    (root/"wikiai/index.md").write_text(
        "# WikiAI.hu\n\n## Szemelyek\n\n- [Molnar Andras](people/molnar-andras.md)\n\n"
        "## Gepi index\n\n- [WikiAI manifest](manifest.json)\n",encoding="utf-8")


class KnowledgeTests(unittest.TestCase):
    def test_dynamic_profiles_only(self):
        docs, people = mod.discover(pages())
        self.assertEqual(len(docs),5)
        self.assertEqual(len(people),3)
        self.assertEqual([p["id"] for p,_,_,_ in people],[143,144,1334])
        self.assertNotIn(145,[p["id"] for p,_,_,_ in people])

    def test_future_personnel_changes_without_simon(self):
        team = [p for p in pages() if p["id"] != 1334]
        team.append(page(1880,"uj-tanacsado","Új tanácsadó",
                         "https://www.wikiai.hu/szakertok/uj-tanacsado/"))
        docs, people = mod.discover(team)
        self.assertEqual([p["id"] for p,_,_,_ in people], [143,144,1880])
        self.assertNotIn(1334,[p["id"] for p,_,_,_ in people])

    def test_absent_required_page_blocks(self):
        with self.assertRaisesRegex(RuntimeError,"Required"):
            mod.discover([p for p in pages() if p["id"]!=22])

    def test_validated_wp_urls(self):
        with self.assertRaises(ValueError):
            mod.canonical("http://www.wikiai.hu/szakertok/varhelyi-csanad/")
        with self.assertRaises(ValueError):
            mod.canonical("https://evil.example/szakertok/varhelyi-csanad/")
        self.assertEqual(mod.canonical("https://www.wikiai.hu/szakertok/simon-imre/"),
                         "https://www.wikiai.hu/szakertok/simon-imre/")

    def test_index_removes_deleted_person_and_adds_simon(self):
        p=mod.discover(pages())[1]
        old="# WikiAI\n\n## Szemelyek\n\n- [Molnar Andras](people/molnar-andras.md)\n\n## Gepi index\n\nEnd\n"
        new=mod.update_index(old,p)
        self.assertNotIn("Molnar",new)
        self.assertIn("people/simon-imre.md",new)
        self.assertIn("people/varhelyi-csanad.md",new)

    def test_manifest_uses_dynamic_people(self):
        docs,p=mod.discover(pages())
        roles={143:"founder",144:"cofounder",1334:"external_professional_partner"}
        out=mod.update_manifest(docs,p,roles,"2026-10-17T11:00:00+00:00",
            {"people":[{"wordpress_post_id":145,"name":"Molnár András"}],"documents":[]})
        self.assertEqual(len(out["people"]),3)
        self.assertEqual(out["people"][2]["name"],"Simon Imre")
        self.assertNotIn("Molnár",json.dumps(out,ensure_ascii=False))

    def test_source_modification_timestamp_equivalence(self):
        self.assertEqual(mod.source_modified_from_md(
            '---\nsource_last_modified: "2026-10-09T15:39:06Z"\n---\n'),
            "2026-10-09T15:39:06+00:00")
        self.assertEqual(mod.source_modified_from_md(
            "source_last_modified: '2026-10-09T15:39:06+00:00'"),
            "2026-10-09T15:39:06+00:00")

    def test_no_content_rewrite_for_unchanged_legacy_mirror(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fixtures(root)
            def fake_get_json(part,query):
                if part=="pages":
                    return pages()
                raise AssertionError("Unchanged pages must not be refetched")
            with patch.object(mod,"ROOT",root), patch.object(mod,"STATE",root/"wikiai/knowledge-sync-state.json"), \
                 patch.object(mod,"STATUS",root/"wikiai/knowledge-sync-status.json"), \
                 patch.object(mod,"KNOWLEDGE_MANIFEST",root/"wikiai/manifest.json"), \
                 patch.object(mod,"INDEX",root/"wikiai/index.md"), \
                 patch.object(mod,"get_json",side_effect=fake_get_json):
                mod.main()
                m=json.loads((root/"wikiai/manifest.json").read_text())
                self.assertEqual(len(m["people"]),3)
                self.assertEqual(m["people"][-1]["name"],"Simon Imre")
                self.assertNotIn("molnar", (root/"wikiai/index.md").read_text().lower())
                state=json.loads((root/"wikiai/knowledge-sync-state.json").read_text())
                self.assertEqual(len(state["managed"]),8)
                self.assertIn("wikiai/people/simon-imre.md",state["managed"])

    def test_non_partner_must_not_be_invented(self):
        p=page(4567,"uj-szakerto","Új szakértő",
               "https://www.wikiai.hu/szakertok/uj-szakerto/")
        record=(p,"person_profile","wikiai/people/uj-szakerto.md","external_professional_partner")
        self.assertEqual(mod.profile_role(record,"<div>Szakterület</div>"),"professional_profile")
        self.assertEqual(mod.profile_role(record,'<div data-entity-role="external-professional-partner">'),"external_professional_partner")


if __name__ == "__main__":
    unittest.main()
