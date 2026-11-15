#!/usr/bin/env python3
"""Read-only, fail-closed mirror of exactly one public WikiAI WordPress post.

Canonical editorial authority: https://www.wikiai.hu/ai-percek-wikiai-podcast/
GitHub is a secondary, reproducible machine-readable mirror. Nothing writes to WP.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlparse

POST_ID = 1946
CANONICAL = "https://www.wikiai.hu/ai-percek-wikiai-podcast/"
REST_BASE = "https://www.wikiai.hu/wp-json/wp/v2/posts/1946"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "wikiai" / "podcasts" / "ai-percek"
YOUTUBE = re.compile(r"https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])")
EPISODE_HEADING = re.compile(
    r'<h3\b[^>]*\bid=["\']epizod-(\d{2})["\'][^>]*>(.*?)</h3>', re.I | re.S
)
EXPECTED_MIN_EPISODES = 3


class TextOnly(HTMLParser):
    BLOCKS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
              "li", "summary", "br", "blockquote", "section", "article"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self.skip += 1
        if tag in self.BLOCKS and not self.skip:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag in self.BLOCKS and not self.skip:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def visible_text(value: str) -> str:
    parser = TextOnly()
    parser.feed(value)
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()

def clean_inline(value: str) -> str:
    return re.sub(r"\s+", " ", visible_text(value)).strip()


def fetch_public_post() -> dict:
    fields = "id,status,slug,link,modified,title,excerpt,content"
    url = REST_BASE + "?" + urlencode({"_fields": fields, "context": "view"})
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "WikiAI-Podcast-Mirror/1.0 (public single-post reader)",
    })
    with urllib.request.urlopen(req, timeout=35) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "www.wikiai.hu":
            raise ValueError("Unexpected redirect outside canonical WordPress host")
        if response.status != 200:
            raise ValueError(f"Unexpected HTTP status: {response.status}")
        payload = response.read(4_000_001)
        if len(payload) > 4_000_000:
            raise ValueError("Unusually large WP response; refusing to mirror")
    data = json.loads(payload.decode("utf-8"))
    if (data.get("id") != POST_ID or data.get("status") != "publish"
            or data.get("slug") != "ai-percek-wikiai-podcast"
            or data.get("link") != CANONICAL):
        raise ValueError("Unexpected WordPress post identity, status or canonical URL")
    content = data.get("content", {}).get("rendered", "")
    if len(content) < 10_000:
        raise ValueError("Published WordPress content is missing or suspiciously short")
    return data


def parse_episode(content: str, heading: re.Match, next_start: int) -> dict:
    number = int(heading.group(1))
    suffix = f"{number:02d}"
    title = clean_inline(heading.group(2))
    segment = content[heading.end():next_start]
    video = YOUTUBE.search(segment)
    if not video:
        raise ValueError(f"Episode {suffix} is missing its embedded YouTube video")
    if len(set(YOUTUBE.findall(segment))) != 1:
        raise ValueError(f"Ambiguous videos in episode {suffix}")
    transcript_match = re.search(
        rf'<details\b[^>]*\bid=["\']atirat-{suffix}["\'][^>]*>(.*?)</details>',
        content, re.I | re.S,
    )
    if not transcript_match:
        raise ValueError(f"Episode {suffix} has no full timestamped transcript")
    paragraphs = re.findall(r"<p\b[^>]*>.*?</p>", transcript_match.group(1), re.I | re.S)
    timed = []
    for paragraph in paragraphs:
        text = clean_inline(paragraph)
        stamp = re.match(r"^\[(\d{2}:\d{2})\]\s*(.+)", text)
        if stamp:
            timed.append({"at": stamp.group(1), "text": stamp.group(2)})
    if len(timed) < 6 or sum(len(x["text"]) for x in timed) < 1500:
        raise ValueError(f"Episode {suffix} transcript is missing or too short")
    times = [int(x["at"][:2]) * 60 + int(x["at"][3:]) for x in timed]
    if times[0] > 20 or times != sorted(times):
        raise ValueError(f"Episode {suffix} time markers are inconsistent")
    intro = clean_inline(segment.split("<!-- wp:embed")[0])
    return {
        "number": number, "id": f"epizod-{suffix}", "title": title,
        "canonical_url": CANONICAL + f"#epizod-{suffix}",
        "transcript_url": CANONICAL + f"#atirat-{suffix}",
        "youtube_url": f"https://www.youtube.com/watch?v={video.group(1)}",
        "youtube_id": video.group(1),
        "description": intro[:2400],
        "timed_transcript": timed,
    }


def extract_episodes(content: str) -> list[dict]:
    matches = list(EPISODE_HEADING.finditer(content))
    if len(matches) < EXPECTED_MIN_EPISODES:
        raise ValueError("Fewer than three published podcast episodes")
    episodes = []
    for index, heading in enumerate(matches):
        rest = content[heading.end():]
        boundary = re.search(r"<h[23]\b", rest, re.I)
        next_start = heading.end() + boundary.start() if boundary else len(content)
        episodes.append(parse_episode(content, heading, next_start))
    numbers = [e["number"] for e in episodes]
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError("Episode numbers must be unique and consecutive starting at 1")
    return episodes


def previous_guard(episodes: list[dict]) -> None:
    path = OUT / "manifest.json"
    if not path.exists():
        return
    old = json.loads(path.read_text(encoding="utf-8"))
    if old.get("wordpress_post_id") != POST_ID or old.get("canonical_url") != CANONICAL:
        raise ValueError("Existing mirror has a different source identity")
    old_episodes = old.get("episodes", [])
    if len(episodes) < len(old_episodes):
        raise ValueError("Episode count shrank; requires editorial review")
    now = {e["number"]: e for e in episodes}
    for item in old_episodes:
        n = item["number"]
        if n not in now or item["youtube_url"] != now[n]["youtube_url"]:
            raise ValueError(f"Episode {n} identity/video changed; review required")
        old_file = OUT / "transcripts" / f"{n:02d}.md"
        if old_file.exists():
            prior = old_file.read_text(encoding="utf-8")
            current = transcript_markdown(now[n])
            if len(current) < len(prior) * 0.7:
                raise ValueError(f"Transcript {n} shrank unusually; review required")


def transcript_markdown(episode: dict) -> str:
    lines = [f"# AI Percek #{episode['number']:02d} — teljes magyar átirat",
             "", f"**Forrás:** {episode['transcript_url']}",
             f"**YouTube:** {episode['youtube_url']}",
             "**Állapot:** SRT-alapú, időjelöléses, publikált szöveg.",
             "", "A beszélt nyelv természetes fordulatait a forrásból megőrizzük.", ""]
    for cue in episode["timed_transcript"]:
        lines.append(f"**[{cue['at']}]** {cue['text']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def episode_markdown(episode: dict) -> str:
    metadata = {
        "document_type": "podcast_episode",
        "language": "hu-HU",
        "episode_number": episode["number"],
        "canonical_url": episode["canonical_url"],
        "youtube_url": episode["youtube_url"],
        "transcript_url": episode["transcript_url"],
        "source_of_truth": "wordpress",
    }
    frontmatter = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}"
                            for k, v in metadata.items())
    return (f"---\n{frontmatter}\n---\n\n# {episode['title']}\n\n"
            f"{episode['description']}\n\n"
            f"[Teljes magyar átirat](../transcripts/{episode['number']:02d}.md) · "
            f"[Eredeti epizód]({episode['canonical_url']}) · "
            f"[YouTube]({episode['youtube_url']})\n")


def graph_jsonld(episodes: list[dict], modified: str) -> dict:
    series_id = CANONICAL + "#podcast"
    series = {
        "@type": "PodcastSeries", "@id": series_id,
        "name": "AI Percek", "inLanguage": "hu-HU",
        "url": CANONICAL,
        "description": "A wikiAI.hu magyar nyelvű, közérthető szakmai podcastja a webfejlesztésről, a Google-keresésről és az AI-láthatóságról.",
        "publisher": {"@id": "https://www.wikiai.hu/#organization"},
        "mainEntityOfPage": {"@id": CANONICAL},
        "episode": [{"@id": e["canonical_url"]} for e in episodes],
    }
    nodes = [series]
    for e in episodes:
        nodes.append({
            "@type": "PodcastEpisode", "@id": e["canonical_url"],
            "name": e["title"], "episodeNumber": e["number"],
            "description": e["description"],
            "inLanguage": "hu-HU",
            "url": e["canonical_url"],
            "partOfSeries": {"@id": series_id},
            "transcript": {"@type": "CreativeWork",
                           "@id": e["transcript_url"],
                           "inLanguage": "hu-HU",
                           "url": e["transcript_url"]},
            "associatedMedia": {
                "@type": "VideoObject",
                "@id": e["youtube_url"],
                "url": e["youtube_url"],
                "embedUrl": f"https://www.youtube.com/embed/{e['youtube_id']}",
                "name": e["title"],
            },
        })
    return {"@context": "https://schema.org", "@graph": nodes}


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def run() -> None:
    post = fetch_public_post()
    markup = post["content"]["rendered"]
    episodes = extract_episodes(markup)
    previous_guard(episodes)
    hash_html = hashlib.sha256(markup.encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "collection": "AI Percek",
        "language": "hu-HU",
        "publisher": "WikiAI.hu",
        "source_of_truth": "WordPress",
        "sync_direction": "wordpress-to-github",
        "wordpress_post_id": POST_ID,
        "canonical_url": CANONICAL,
        "wordpress_modified": post["modified"],
        "html_sha256": hash_html,
        "spotify_show_url": "https://open.spotify.com/show/0kBSFHE2qHO8xSzi7pB5BJ",
        "apple_podcasts_show_url": "https://podcasts.apple.com/podcast/id6834785544",
        "episodes": [{
            "number": e["number"], "id": e["id"], "name": e["title"],
            "canonical_url": e["canonical_url"],
            "transcript_url": e["transcript_url"],
            "youtube_url": e["youtube_url"],
            "machine_record": f"episodes/{e['number']:02d}.md",
            "transcript_mirror": f"transcripts/{e['number']:02d}.md",
            "timestamped_paragraphs": len(e["timed_transcript"]),
        } for e in episodes],
    }
    files = {
        OUT / "manifest.json": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        OUT / "article.html": markup.rstrip() + "\n",
        OUT / "article.txt": (
            clean_inline(post["title"]["rendered"]) + "\n"
            + CANONICAL + "\n\n" + visible_text(markup).rstrip() + "\n"
        ),
        OUT / "knowledge-graph.jsonld": json.dumps(
            graph_jsonld(episodes, post["modified"]), indent=2, ensure_ascii=False
        ) + "\n",
    }
    for e in episodes:
        files[OUT / "episodes" / f"{e['number']:02d}.md"] = episode_markdown(e)
        files[OUT / "transcripts" / f"{e['number']:02d}.md"] = transcript_markdown(e)
    changes = sum(write_if_changed(path, content) for path, content in files.items())
    print(f"AI Percek: source post {POST_ID}; {len(episodes)} episodes; "
          f"{len(files)} mirror files; {changes} changed; WP modified {post['modified']}.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"FAIL-CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
