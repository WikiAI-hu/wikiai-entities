#!/usr/bin/env python3
"""Offline regression tests for the AI Percek one-post public mirror."""
# Manual read-only WordPress mirror refresh trigger: 2026-11-21 (AI Percek #05).
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("sync-ai-percek.py")
spec = importlib.util.spec_from_file_location("sync_ai_percek", MODULE_PATH)
sync = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(sync)


def fixture(count=3):
    html = "<h2>Az AI Percek epizódjai</h2>"
    for n in range(1, count + 1):
        label = f"{n:02d}"
        video = "https://www.youtube.com/watch?v=" + ("abcdefghij" + str(n % 10))
        html += (f'<h3 id="epizod-{label}">AI Percek #{label} – Teszt</h3>'
                 + '<p>Ez egy valósághű próba leírás, amely az epizódot bemutatja.</p>'
                 + '<!-- wp:embed -->' + video + '<!-- /wp:embed -->')
    html += '<h2 id="teljes-atiratok">Teljes átiratok</h2>'
    for n in range(1, count + 1):
        label = f"{n:02d}"
        paragraphs = "".join(
            f'<p><strong>[00:{i:02d}]</strong> ' +
            ("A teljes magyar átirat meghatározott időpontja és beszélgetési szövege. " * 6)
            + "</p>" for i in range(0, 30, 4)
        )
        html += (f'<details id="atirat-{label}"><summary>Teljes magyar átirat</summary>'
                 + paragraphs + '</details>')
    return html


class ParseTests(unittest.TestCase):
    def test_three_complete_episodes(self):
        episodes = sync.extract_episodes(fixture())
        self.assertEqual([x["number"] for x in episodes], [1, 2, 3])
        self.assertEqual(episodes[2]["youtube_url"],
                         "https://www.youtube.com/watch?v=abcdefghij3")
        self.assertEqual(len(episodes[2]["timed_transcript"]), 8)
        self.assertIn("A teljes magyar átirat", sync.transcript_markdown(episodes[2]))

    def test_new_episode_is_detected_without_code_change(self):
        episodes = sync.extract_episodes(fixture(4))
        self.assertEqual(len(episodes), 4)
        self.assertEqual(episodes[-1]["id"], "epizod-04")

    def test_previous_episode_link_does_not_override_embedded_video(self):
        markup = fixture(5).replace(
            '<h2 id="teljes-atiratok">',
            '<p><a href="https://www.youtube.com/watch?v=abcdefghij4">'
            'Hallgasd meg az előző részt</a></p>'
            '<h2 id="teljes-atiratok">',
        )
        episodes = sync.extract_episodes(markup)
        self.assertEqual(len(episodes), 5)
        self.assertEqual(episodes[-1]["youtube_url"],
                         "https://www.youtube.com/watch?v=abcdefghij5")

    def test_public_rest_without_block_comments_keeps_primary_video(self):
        markup = fixture(5).replace("<!-- wp:embed -->", "").replace(
            "<!-- /wp:embed -->", ""
        )
        markup = markup.replace(
            '<h2 id="teljes-atiratok">',
            '<p><a href="https://www.youtube.com/watch?v=abcdefghij4">'
            'Előző epizód</a></p><h2 id="teljes-atiratok">',
        )
        episodes = sync.extract_episodes(markup)
        self.assertEqual(len(episodes), 5)
        self.assertEqual(episodes[-1]["youtube_id"], "abcdefghij5")

    def test_multiple_embeds_fail_closed_even_if_external_links_exist(self):
        markup = fixture(5).replace(
            '<h2 id="teljes-atiratok">',
            '<!-- wp:embed -->https://www.youtube.com/watch?v=abcdefghij4'
            '<!-- /wp:embed --><h2 id="teljes-atiratok">',
        )
        with self.assertRaisesRegex(ValueError, "exactly one YouTube embed"):
            sync.extract_episodes(markup)

    def test_missing_transcript_fails_closed(self):
        markup = fixture().replace('id="atirat-03"', 'id="wrong-03"')
        with self.assertRaisesRegex(ValueError, "no full timestamped transcript"):
            sync.extract_episodes(markup)

    def test_invalid_video_fails_closed(self):
        markup = fixture().replace("watch?v=abcdefghij2", "watch?v=INVALIDVIDEO")
        with self.assertRaisesRegex(ValueError, "missing its embedded YouTube"):
            sync.extract_episodes(markup)

    def test_missing_episode_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Fewer than three"):
            sync.extract_episodes(fixture(2))

    def test_post_identity_is_fixed(self):
        self.assertEqual(sync.POST_ID, 1946)
        self.assertEqual(sync.CANONICAL,
                         "https://www.wikiai.hu/ai-percek-wikiai-podcast/")

    def test_jsonld_graph_has_exact_episode_identity(self):
        ep = sync.extract_episodes(fixture())
        graph = sync.graph_jsonld(ep, "2026-11-15T12:24:13")
        self.assertEqual(len(graph["@graph"]), 4)
        self.assertEqual(graph["@graph"][0]["@type"], "PodcastSeries")
        self.assertEqual(graph["@graph"][3]["@id"],
                         "https://www.wikiai.hu/ai-percek-wikiai-podcast/#epizod-03")

    def test_guard_rejects_deleted_episodes(self):
        with tempfile.TemporaryDirectory() as folder:
            original_out = sync.OUT
            try:
                sync.OUT = Path(folder)
                sync.OUT.mkdir(parents=True, exist_ok=True)
                data = {"wordpress_post_id": 1946,
                        "canonical_url": sync.CANONICAL,
                        "episodes": [{"number": i,
                                      "youtube_url": f"https://www.youtube.com/watch?v=abcdefghij{i}"}
                                     for i in range(1, 5)]}
                (sync.OUT / "manifest.json").write_text(
                    json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "count shrank"):
                    sync.previous_guard(sync.extract_episodes(fixture(3)))
            finally:
                sync.OUT = original_out

    def test_timestamp_preserved(self):
        ep = sync.extract_episodes(fixture())[0]
        s = sync.transcript_markdown(ep)
        self.assertIn("**[00:00]**", s)
        self.assertIn("**[00:28]**", s)


if __name__ == "__main__":
    unittest.main()
