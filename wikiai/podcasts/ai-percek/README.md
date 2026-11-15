# AI Percek – gépileg olvasható podcasttükör

**Hiteles elsődleges forrás:** [AI Percek – wikiAI.hu Tudástár](https://www.wikiai.hu/ai-percek-wikiai-podcast/) · **WordPress post ID: 1946**.

Ez a könyvtár **kizárólag** a fenti, nyilvánosan közzétett Tudástár-bejegyzés ellenőrzött, verziózott tükre. A WordPress szerkesztőségi tartalma az irányadó, nem a GitHub. A repó nem szerkeszti a WordPress-oldalt, nem kapcsolódik az ügyfélprofilok `entities/` szinkronjához, és nem tesz automatikusan közzé új epizódot.

## Miről szól a sorozat?

Az **AI Percek** a wikiAI.hu rövid, közérthető, magyar nyelvű szakmai podcast- és videósorozata: webfejlesztés, keresőoptimalizálás, Google-keresés, AI-láthatóság és a magyar vállalkozások digitális jelenléte. A beszélgetésekhez AI-generált műsorvezetői hangokat használnak; a wikiAI.hu felelős szerkesztője Várhelyi Csanád.

- **YouTube:** [wikiAI.hu-csatorna](https://www.youtube.com/channel/UCvUWrv3dXJCOM791G2d2tfQ)
- **Spotify:** [AI Percek](https://open.spotify.com/show/0kBSFHE2qHO8xSzi7pB5BJ)
- **Apple Podcasts:** [AI Percek](https://podcasts.apple.com/podcast/id6834785544)
- **Ember számára hiteles forrás:** https://www.wikiai.hu/ai-percek-wikiai-podcast/

## Automatikusan előállított fájlok

Az első sikeres futás után a következő fájlok készülnek:

| Fájl | Rendeltetés |
|---|---|
| `manifest.json` | Stabil epizódazonosítók, források, módosítási és tartalmi ellenőrzőadatok |
| `article.html` | A közzétett WordPress-cikk teljes HTML-tartalmának másolata |
| `article.txt` | A cikk kereshető, tisztított szövegváltozata |
| `knowledge-graph.jsonld` | Az ismert, nyilvánosan igazolt PodcastSeries / PodcastEpisode kapcsolatok |
| `episodes/01.md`, `02.md`, … | Külön epizódrekordok |
| `transcripts/01.md`, `02.md`, … | A WordPressben látható teljes magyar időjelöléses átiratok |

A gépi adatok **nem** jelentenek hivatalos Google- vagy AI-rangsorolási jóváhagyást. A JSON-LD a GitHubon másodlagos tükrözés; nem kerül automatikusan a WordPress fejlécébe. A Google elsődlegesen a kanonikus WordPress-oldalt indexelheti.

## Hogyan frissül?

1. A szerkesztő előbb **a WordPress #1946-es AI Percek cikkébe** teszi be az új részt, annak YouTube-videóját és teljes `<details id="atirat-XX">` átiratát.
2. A `<h3 id="epizod-XX">` cím és a `<details id="atirat-XX">` azonosító ugyanazt a kétjegyű epizódsorszámot tartalmazza.
3. A [külön GitHub Actions feladat](../../../.github/workflows/sync-ai-percek.yml) körülbelül háromóránként, illetve kézi indításkor elolvassa **csak** a nyilvános WordPress REST API `/wp-json/wp/v2/posts/1946` válaszát.
4. A kód ellenőrzi a cikkazonosítót, a közzétett állapotot, a kanonikus URL-t, az egymást követő epizódszámokat, az egyértelmű YouTube-videókat és az átiratok épségét.
5. Sikeres ellenőrzés után **csak** a `wikiai/podcasts/ai-percek/` mappa változó fájljait írja be a repóba. Változatlan tartalom nem generál új commitot.

**Műveletileg fontos:** ha csak a YouTube-ra vagy Spotify-ra töltesz fel új epizódot, de a WordPress-bejegyzésben még nincs róla teljes adatlap és időjelöléses átirat, a szinkron **nem** talál ki vagy publikál helyette új részt. Ilyenkor előbb frissíteni kell a WordPress-cikket.

## Biztonsági korlátok

- Egyetlen engedélyezett WordPress-bejegyzés: **1946**; a többi Tudástár- és Vállalkozások-bejegyzés érintetlen.
- Egyirányú, publikus **WordPress → GitHub** adatáramlás; nincs WordPress hitelesítési adat vagy írási jogosultság.
- Hibás WordPress-válasz, hiányzó átirat, megváltozott YouTube-azonosító vagy jelentős tartalomcsökkenés esetén a frissítés leáll.
- Nem találunk ki megjelenési dátumot, lejátszási számot, értékelést, szerzői szerepet, AI-ajánlási garanciát vagy nem publikált műszaki know-how-t.
- Az `entities/`, `wikiai/people/`, `wikiai/manifest.json` és a meglévő HFCM JSON-LD szinkronizáló fájlok változatlanok.

**Manuális indítás:** GitHub → Actions → **Mirror AI Percek single WordPress article** → **Run workflow**.

**Technikai forrás:** `.github/scripts/sync-ai-percek.py` · **tesztek:** `.github/scripts/test_sync_ai_percek.py`.
