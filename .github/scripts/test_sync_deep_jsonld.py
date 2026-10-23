import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

P = Path(__file__).with_name('sync-deep-jsonld.py')
spec = importlib.util.spec_from_file_location('wikiai_jsonld_sync', P)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
CANON = 'https://www.wikiai.hu/pelda-vallalkozas/'


def sample(business_id=None, nodes=14, role_override=False):
    business_id = business_id or 'https://pelda-vallalkozas.hu/#organization'
    graph = [
        {'@type': 'Organization', '@id': 'https://www.wikiai.hu/#organization', 'name': 'WikiAI.hu'},
        {'@type': ['WebPage', 'ProfilePage'], '@id': CANON + '#webpage', 'url': CANON, 'mainEntity': {'@id': business_id}},
        {'@type': 'Article', '@id': CANON + '#article', 'url': CANON, 'mainEntity': {'@id': business_id},
         'author': {'@id': 'https://www.wikiai.hu/szakertok/varhelyi-csanad/#person'},
         'editor': {'@id': 'https://www.wikiai.hu/szakertok/varhelyi-csanad/#person'},
         'accountablePerson': {'@id': 'https://www.wikiai.hu/szakertok/varhelyi-csanad/#person'}},
        {'@type': ['Organization', 'LocalBusiness'], '@id': business_id, 'name': 'Példa Vállalkozás'},
    ]
    for i in range(nodes - 4):
        graph.append({'@type': 'Thing', '@id': CANON + f'#topic-{i}', 'name': f'Topic {i}'})
    if role_override:
        del graph[2]['author']
    return {'@context': 'https://schema.org', '@graph': graph}


def wrap(*scripts):
    return '<html><head>' + ''.join('<script type="application/ld+json">' + (s if isinstance(s, str) else json.dumps(s)) + '</script>' for s in scripts) + '</head><body>content</body></html>'


class TestMirror(unittest.TestCase):
    def test_select_deep_and_ignore_other_valid_script(self):
        data = mod.find_deep_graph(wrap({'@context': 'https://schema.org', '@type': 'WebSite', 'name':'WikiAI'}, sample()), CANON)
        self.assertEqual(data['nodes'], 14)
        self.assertEqual(data['business_id'], 'https://pelda-vallalkozas.hu/#organization')

    def test_multiple_deep_graphs_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Expected one'):
            mod.find_deep_graph(wrap(sample(), sample()), CANON)

    def test_jsonld_parse_failure_is_fatal(self):
        with self.assertRaisesRegex(ValueError, 'Invalid head JSON-LD'):
            mod.find_deep_graph(wrap('{invalid', sample()), CANON)

    def test_missing_or_crossed_entity_not_accepted(self):
        data = sample()
        data['@graph'][2]['mainEntity'] = {'@id': 'https://different.com/#business'}
        with self.assertRaisesRegex(ValueError, 'Expected one'):
            mod.find_deep_graph(wrap(data), CANON)

    def test_legacy_custom_business_ids_and_valid_doc(self):
        for suffix in ['#business', '#restaurant', '#organization']:
            result = mod.find_deep_graph(wrap(sample('https://other-brand.example/' + suffix)), CANON)
            self.assertIn(suffix, result['business_id'])

    def test_csanad_role_warning_not_silent_override(self):
        d = sample(role_override=True)
        result = mod.find_deep_graph(wrap(d), CANON)
        self.assertTrue(any('author' in x for x in result['warnings']))
        self.assertNotIn('author', d['@graph'][2])

    def test_valid_mainentityofpage_reference_and_optional_editor_fields(self):
        data = sample()
        article = data['@graph'][2]
        article['mainEntityOfPage'] = {'@id': CANON}
        del article['editor']
        del article['accountablePerson']
        result = mod.find_deep_graph(wrap(data), CANON)
        self.assertFalse(any(
            'Article.mainEntityOfPage' in warning or
            'Article.editor' in warning or
            'Article.accountablePerson' in warning
            for warning in result['warnings']
        ))

    def test_mainentityofpage_object_without_id_warns(self):
        data = sample()
        data['@graph'][2]['mainEntityOfPage'] = {'@type': 'WebPage'}
        result = mod.find_deep_graph(wrap(data), CANON)
        self.assertTrue(any('mainEntityOfPage object lacks an @id' in x for x in result['warnings']))

    def test_explicit_wrong_editor_is_flagged(self):
        data = sample()
        data['@graph'][2]['editor'] = {'@id': 'https://example.com/#different-person'}
        result = mod.find_deep_graph(wrap(data), CANON)
        self.assertTrue(any('Article.editor' in warning for warning in result['warnings']))

    def test_legacy_varganya_article_about_restaurant(self):
        data = sample('https://restaurant.example/#restaurant')
        data['@graph'] = [n for n in data['@graph'] if 'WebPage' not in mod.node_types(n)]
        article = next(n for n in data['@graph'] if 'Article' in mod.node_types(n))
        del article['mainEntity']
        article['mainEntityOfPage'] = CANON
        article['about'] = [{'@id': 'https://restaurant.example/#restaurant'}]
        business = next(n for n in data['@graph'] if n.get('@id') == 'https://restaurant.example/#restaurant')
        business['@type'] = 'Restaurant'
        result = mod.find_deep_graph(wrap(data), CANON)
        self.assertEqual(result['business_id'], business['@id'])
        self.assertTrue(any('Legacy Article' in w for w in result['warnings']))

    def test_kohlberger_compact_prefixes(self):
        data = sample('kb:business')
        data['@context'] = ['https://schema.org', {'kb': CANON + '#', 'wi': 'https://www.wikiai.hu/#', 'vc': 'https://www.varhelyicsanad.hu/#'}]
        data['@graph'][0]['@id'] = 'wi:organization'
        article = data['@graph'][2]
        article['@id'] = 'kb:article'
        del article['url']
        for role in ('author','editor','accountablePerson'):
            article[role] = {'@id':'vc:person'}
        data['@graph'][1]['@id'] = 'kb:webpage'
        result = mod.find_deep_graph(wrap(data), CANON)
        self.assertEqual(result['business_id'], 'kb:business')
        self.assertTrue(any('Article.author' in w and 'retired' in w for w in result['warnings']))

    def test_canonical_csanad_person_id_no_deprecation_warning(self):
        result = mod.find_deep_graph(wrap(sample()), CANON)
        self.assertFalse(any('retired' in w for w in result['warnings']))

    def test_retired_person_id_warns_without_rewriting_source(self):
        data = sample()
        data['@graph'][2]['author'] = {'@id': 'https://www.varhelyicsanad.hu/#person'}
        result = mod.find_deep_graph(wrap(data), CANON)
        self.assertTrue(any('Article.author' in w and 'retired' in w for w in result['warnings']))
        self.assertEqual(data['@graph'][2]['author']['@id'], 'https://www.varhelyicsanad.hu/#person')

    def test_managed_file_guard_and_legacy_adoption(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base/'entities').mkdir()
            (base/'entities'/'pelda-vallalkozas.md').write_text('ok', encoding='utf-8')
            target = base/'entities'/'pelda-vallalkozas.jsonld'
            base_graph = sample()
            target.write_text(json.dumps(base_graph), encoding='utf-8')
            fixture = base/'page.html'
            fixture.write_text(wrap(sample()), encoding='utf-8')
            entry = {'canonical_url':CANON, 'machine_record':'entities/pelda-vallalkozas.md'}
            with patch.object(mod, 'ROOT', base):
                tracked = {}
                output = mod.sync_entry(entry, tracked, '2026-10-17T12:00:00Z', fixture)
                self.assertEqual(output['change'], 'adopted')
                self.assertEqual(tracked['pelda-vallalkozas']['legacy_original_sha256'], mod.sha256(json.dumps(base_graph)))
                target.write_text(target.read_text(encoding='utf-8') + '\n', encoding='utf-8')
                with self.assertRaisesRegex(RuntimeError, 'outside sync'):
                    mod.sync_entry(entry, tracked, '2026-10-17T12:01:00Z', fixture)

    def test_legacy_drift_updates_live_without_losing_business_id(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base/'entities').mkdir()
            (base/'entities'/'pelda-vallalkozas.md').write_text('ok')
            target = base/'entities'/'pelda-vallalkozas.jsonld'
            target.write_text(json.dumps(sample(nodes=14)))
            future = sample(nodes=16)
            fixture = base/'page.html'
            fixture.write_text(wrap(future))
            entry = {'canonical_url':CANON, 'machine_record':'entities/pelda-vallalkozas.md'}
            with patch.object(mod, 'ROOT', base):
                result = mod.sync_entry(entry, {}, '2026-10-17T12:00:00Z', fixture)
                self.assertEqual(result['change'], 'updated')
                self.assertEqual(len(json.loads(target.read_text())['@graph']), 16)

    def test_historic_business_iri_change_with_same_name_is_migrated(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base/'entities').mkdir()
            (base/'entities'/'pelda-vallalkozas.md').write_text('ok')
            old = sample(CANON + '#restaurant')
            (base/'entities'/'pelda-vallalkozas.jsonld').write_text(json.dumps(old))
            fixture = base/'site.html'
            fixture.write_text(wrap(sample('https://restaurant.example/#restaurant')))
            entry = {'canonical_url':CANON, 'machine_record':'entities/pelda-vallalkozas.md'}
            with patch.object(mod, 'ROOT', base):
                result = mod.sync_entry(entry, {}, '2026-10-17T12:00:00Z', fixture)
                self.assertEqual(result['change'], 'updated')
                self.assertTrue(any('Legacy business' in x for x in result['warnings']))

    def test_historic_restaurant_managed_identity_change_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base/'entities').mkdir()
            (base/'entities'/'pelda-vallalkozas.md').write_text('ok')
            original = sample('https://restaurant.example/#restaurant')
            original['@graph'] = [n for n in original['@graph'] if 'WebPage' not in mod.node_types(n)]
            article = next(n for n in original['@graph'] if 'Article' in mod.node_types(n))
            article.pop('mainEntity')
            article['mainEntityOfPage'] = CANON
            article['about'] = [{'@id': 'https://restaurant.example/#restaurant'}]
            original['@graph'][2]['@type'] = 'Restaurant'
            live = sample('https://different.example/#restaurant')
            target = base/'entities'/'pelda-vallalkozas.jsonld'
            target.write_text(json.dumps(original))
            fixture = base/'live.html'
            fixture.write_text(wrap(live))
            entry = {'canonical_url':CANON, 'machine_record':'entities/pelda-vallalkozas.md'}
            with patch.object(mod, 'ROOT', base):
                prior = mod.prior_main_entity(original, CANON)
                self.assertEqual(prior, 'https://restaurant.example/#restaurant')
                managed = {'pelda-vallalkozas': {'sha256':mod.sha256(target.read_text())}}
                with self.assertRaisesRegex(RuntimeError, 'Managed business identity'):
                    mod.sync_entry(entry, managed, '2026-10-17T12:00:00Z', fixture)

    def test_historic_business_iri_change_name_mismatch_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base/'entities').mkdir()
            (base/'entities'/'pelda-vallalkozas.md').write_text('ok')
            old = sample(CANON + '#restaurant')
            old['@graph'][3]['name'] = 'Másik vállalkozás'
            (base/'entities'/'pelda-vallalkozas.jsonld').write_text(json.dumps(old))
            fixture = base/'site.html'
            fixture.write_text(wrap(sample('https://restaurant.example/#restaurant')))
            entry = {'canonical_url':CANON, 'machine_record':'entities/pelda-vallalkozas.md'}
            with patch.object(mod, 'ROOT', base):
                with self.assertRaisesRegex(RuntimeError, 'without matching entity name'):
                    mod.sync_entry(entry, {}, '2026-10-17T12:00:00Z', fixture)

    def test_shrinking_old_graph_requires_manual_review(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base/'entities').mkdir()
            (base/'entities'/'pelda-vallalkozas.md').write_text('ok')
            target = base/'entities'/'pelda-vallalkozas.jsonld'
            target.write_text(json.dumps(sample(nodes=80)))
            fixture = base/'page.html'
            fixture.write_text(wrap(sample(nodes=14)))
            entry = {'canonical_url':CANON, 'machine_record':'entities/pelda-vallalkozas.md'}
            with patch.object(mod, 'ROOT', base):
                managed = {'pelda-vallalkozas': {'sha256':mod.sha256(target.read_text())}}
                with self.assertRaisesRegex(RuntimeError, 'shrank unexpectedly'):
                    mod.sync_entry(entry, managed, '2026-10-17T12:00:00Z', fixture)

    def test_slug_and_host_guards(self):
        with self.assertRaisesRegex(ValueError, 'canonical'):
            mod.parse_profile({'canonical_url':'https://evil.com/pelda-vallalkozas/','machine_record':'entities/pelda-vallalkozas.md'})
        with self.assertRaisesRegex(ValueError, 'Manifest'):
            mod.parse_profile({'canonical_url':CANON,'machine_record':'entities/other.md'})


if __name__ == '__main__':
    unittest.main()
