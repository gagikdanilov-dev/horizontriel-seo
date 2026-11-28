"""Offline integration tests for generated pages, not production records.

Run from seo/: python -m unittest discover -s tests -v
All network access is forbidden in the fixture; output/history use a temp dir.
"""
from contextlib import ExitStack, contextmanager, redirect_stdout
from datetime import datetime, timezone
from html.parser import HTMLParser
import io
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit, unquote
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build
import config as C
import geography
import templates
from listing_contract import country_for, currency_for, is_recent_listing, newest_first


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.elements, self.structured = [], []
        self._ld = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._ld = []

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.structured.append(json.loads("".join(self._ld)))
            self._ld = None

    def tags(self, tag, **attrs):
        return [a for t, a in self.elements if t == tag and all(a.get(k) == v for k, v in attrs.items())]

    def card_links(self, class_name="card"):
        return [a["href"] for a in self.tags("a") if class_name in a.get("class", "").split()]


def record(suffix, **overrides):
    result = {
        "id": "synthetic" + suffix, "title": "Объект " + suffix, "type": "Квартира",
        "region": "Ставропольский край", "city": "Кисловодск", "deal": "Продажа",
        "price": 1_200_000, "rooms": 2, "area": 60, "published": True,
        "created": "2026-10-01 10:00:00.000Z", "updated": "2026-11-30 10:00:00.000Z",
        "images": ["photo.jpg"], "description": "Синтетическая проверочная запись",
    }
    result.update(overrides)
    return result


def inventory():
    return [
        record("ruold1", featured=True),
        record("runew2", published_at="2026-11-25T09:00:00Z", currency="RUB", rooms=3),
        record("cypru3", country="CY", region="Лимасол", city="Одинаковый город", currency="EUR",
               price=285000.75, published_at="2026-11-25T11:00:00+01:00",
               videos=["обзор квартиры.mp4", "tour.webm", "third.MP4", "fourth.mp4"]),
        record("turke4", region="Турция", city="Одинаковый город", currency="TRY", price=5_000_000,
               published_at="2026-11-24T20:00:00Z"),
        record("duba05", country="UAE", region="Дубай", city="Дубай", currency="AED", price=1_450_000,
               published_at="2026-11-26T12:00:00Z"),
        record("spain6", country="Spain", region="Каталония", city="Барселона", currency="EUR", price=450_000,
               published_at="2026-11-25T09:00:00Z", rooms=1),
        record("spusd7", country="Испания", region="Каталония", city="Барселона", currency="USD", price=600_000,
               created="2026-11-23T12:00:00Z", rooms=3),
        record("spunk8", country="Испания", region="Каталония", city="Барселона", price=900_000,
               created="2026-11-22T12:00:00Z"),
        record("draft9", published=False, published_at="2026-11-30T12:00:00Z"),
    ]


@contextmanager
def built(records, paths=None):
    with tempfile.TemporaryDirectory(prefix="horizontriel-seo-tests-") as tmp, ExitStack() as stack:
        root = Path(tmp)
        (root / ".horizontriel-seo-stable-urls.json").write_text(
            json.dumps({"version": 1, "paths": paths or {}}), encoding="utf-8")
        stack.enter_context(patch.object(C, "OUT_DIR", str(root / "dist")))
        stack.enter_context(patch.object(build, "SAMPLE", False))
        stack.enter_context(patch.object(build, "fetch_listings", return_value=records))
        stack.enter_context(patch.object(build, "fetch_settings", return_value=dict(C.FALLBACK_SETTINGS)))
        stack.enter_context(patch("urllib.request.urlopen", side_effect=AssertionError("Network is forbidden in offline tests")))
        log = io.StringIO()
        with redirect_stdout(log):
            build.build()
        yield root, log


def page_text(root, path):
    return (root / "dist" / path.strip("/") / "index.html").read_text(encoding="utf-8")


def paths_for(root):
    return json.loads((root / ".horizontriel-seo-stable-urls.json").read_text())["paths"]


class InternationalIntegration(unittest.TestCase):
    def test_listing_labels_preserve_complex_names_and_distinguish_unit_floor(self):
        valid = record("unit", residential_complex='жк\u00a0«Волна»', floor=6, floors=12, kitchen_area=11.3)
        basement = record("below", description="Первая линия. Цокольный этаж. В продаже два помещения.", floor=1,
                          floors=5, kitchen_area=111, completion_date="т")
        missing = record("unset", residential_complex='«Волна»', floors=12,
                         description="Бассейн занимает цокольный этаж комплекса.")
        self.assertTrue(is_recent_listing({"created":"2026-11-12T00:00:00Z"}, datetime(2026,11,28,tzinfo=timezone.utc)))
        self.assertFalse(is_recent_listing(valid, datetime(2026,11,28,tzinfo=timezone.utc)))
        with built([valid, basement, missing]) as (root, _):
            listing_paths = paths_for(root)
            hub = page_text(root, "/")
            self.assertIn('жк\u00a0«Волна»', hub)
            self.assertIn('ЖК «Волна»', hub)
            self.assertNotIn('ЖК жк', hub)
            self.assertIn('Этаж 6 из 12', hub)
            self.assertIn('Этажность: 12', hub)
            self.assertIn('Цокольный этаж', hub)
            valid_html = page_text(root,listing_paths[valid['id']])
            self.assertIn('11.3 м²', valid_html)
            basement_html = page_text(root,listing_paths[basement['id']])
            self.assertIn('<div class="pval">Цокольный</div>', basement_html)
            self.assertNotIn('111 м²', basement_html)
            self.assertNotIn('Срок сдачи', basement_html)
            missing_html = page_text(root,listing_paths[missing['id']])
            self.assertIn('Этажность', missing_html)

    def test_known_legacy_region_keeps_urls_and_respects_explicit_country_currency(self):
        legacy = record("legacys", country="", region="Ставропольский", currency="", price=13_000_000)
        foreign = record("foreigns", country="Spain", region="Ставропольский", currency="EUR")
        explicit_russia = record("explicitru", country="RU", region="Ставропольский", currency="RUB")
        unknown = record("unknowns", region="Неизвестный регион", city="Кисловодск")
        self.assertEqual(country_for(legacy), "Россия")
        normalized = build.normalize(legacy)
        self.assertEqual((normalized["country"], normalized["currency"], normalized["region"]),
                         ("Россия", "RUB", "Ставропольский"))
        self.assertEqual(currency_for(normalized), "RUB")
        self.assertEqual(geography.location(normalized), ("Россия", "Ставропольский", "Кисловодск"))
        # Preserve regional membership and its established URL scheme as well as raw region.
        self.assertFalse(geography.in_home_region(normalized))
        self.assertEqual(country_for(foreign), "Испания")
        self.assertEqual(build.normalize(foreign)["currency"], "EUR")
        self.assertIsNone(currency_for(dict(foreign, currency="")))
        self.assertEqual(currency_for(dict(legacy, currency="USD")), "USD")
        invalid = build.normalize(dict(legacy, currency="XYZ"))
        self.assertIsNone(invalid["currency"])
        self.assertIsNone(currency_for(invalid))
        self.assertEqual(country_for(unknown), "")
        self.assertIsNone(currency_for(unknown))
        self.assertEqual(country_for(dict(legacy, region="Ставропольский городской")), "")
        self.assertEqual(country_for(dict(legacy, country="Atlantis")), "Atlantis")
        self.assertIsNone(currency_for(dict(legacy, country="Atlantis")))

        retained = {legacy["id"]: "/obekt/already-published-egacys/"}
        # Historical digest of (unknown country, exact legacy region, Кисловодск).
        legacy_directory = "/geografiya/kislovodsk-dda9f2a45f2707b8/kvartiry/"
        with built(inventory() + [legacy, foreign, explicit_russia], retained) as (root, _):
            history = paths_for(root)
            self.assertEqual(history[legacy["id"]], retained[legacy["id"]])
            html = page_text(root, retained[legacy["id"]])
            doc = Document(html)
            self.assertEqual(doc.tags("link", rel="canonical")[0]["href"], C.SITE_BASE + retained[legacy["id"]])
            listing = doc.structured[0]
            self.assertEqual(listing["address"]["addressCountry"], "RU")
            self.assertEqual(listing["address"]["addressRegion"], "Ставропольский")
            self.assertEqual(listing["offers"]["priceCurrency"], "RUB")
            self.assertEqual(listing["offers"]["price"], 13_000_000)
            self.assertIn(C.fmt_price_plain(13_000_000, "RUB"), html)
            foreign_ld = Document(page_text(root, history[foreign["id"]])).structured[0]
            self.assertEqual(foreign_ld["address"]["addressCountry"], "ES")
            self.assertEqual(foreign_ld["address"]["addressRegion"], "Ставропольский")
            self.assertEqual(foreign_ld["offers"]["priceCurrency"], "EUR")
            feed = json.loads((root / "dist/geografiya/cities.json").read_text())
            local = next(x for x in feed["kvartiry"] if x["area"] == "Россия · Ставропольский")
            overseas = next(x for x in feed["kvartiry"] if x["area"] == "Испания · Ставропольский")
            self.assertEqual(local["path"], legacy_directory)
            self.assertEqual(local["count"], 2)
            self.assertEqual(sum(x["area"] == "Россия · Ставропольский" for x in feed["kvartiry"]), 1)
            self.assertNotEqual(overseas["path"], local["path"])
            directory_html = page_text(root, legacy_directory)
            directory = Document(directory_html)
            self.assertEqual(directory.tags("link", rel="canonical")[0]["href"], C.SITE_BASE + legacy_directory)
            self.assertIn(retained[legacy["id"]], directory.card_links())
            self.assertIn(history[explicit_russia["id"]], directory.card_links())
            jumps = [parse_qs(urlsplit(a["href"]).fragment.split("?", 1)[1])
                     for a in directory.tags("a") if "#catalog?" in a.get("href", "")]
            self.assertTrue(any(q.get("geo_country") == ["Россия"] and
                                q.get("geo_region") == ["Ставропольский"] for q in jumps))
            urls = {n.text for n in ET.parse(root / "dist/sitemap.xml").iter() if n.tag.endswith("}loc")}
            for path in [retained[legacy["id"]], legacy_directory, "/gorod/kislovodsk/",
                         "/gorod/kislovodsk/kvartiry/", "/region/stavropolskiy-kray/"]:
                self.assertIn(C.SITE_BASE + path, urls)

    def test_full_build_keeps_international_inventory_and_regional_urls(self):
        rows = inventory()
        with built(rows) as (root, _):
            history = paths_for(root)
            self.assertEqual(set(history), {r["id"] for r in rows if r["published"]})
            sitemap = ET.parse(root / "dist/sitemap.xml")
            locations = [n.text for n in sitemap.iter() if n.tag.endswith("}loc")]
            self.assertEqual(len(locations), len(set(locations)))
            for row in rows:
                if not row["published"]:
                    continue
                path = history[row["id"]]
                self.assertIn(C.SITE_BASE + path, locations)
                doc = Document(page_text(root, path))
                self.assertEqual(doc.tags("link", rel="canonical")[0]["href"], C.SITE_BASE + path)
                self.assertEqual(len(doc.tags("h1")), 1)
            for path in ["/gorod/kislovodsk/", "/region/stavropolskiy-kray/", "/gorod/kislovodsk/kvartiry/", "/lp/podbor-kvartir/"]:
                self.assertIn(C.SITE_BASE + path, locations)
            home = page_text(root, "/")
            self.assertIn("Horizontriel", home)
            self.assertNotIn("ГоризонТРиел", home)
            self.assertIn("в России и за рубежом", home)
            for path in C.COUNTRY_PAGES.values():
                self.assertIn('href="' + C.MAIN_SITE + path + '"', home)
            self.assertIn("geo_country=", home)
            feed = json.loads((root / "dist/geografiya/cities.json").read_text())
            same_name = [x for x in feed["kvartiry"] if x["city"] == "Одинаковый город"]
            self.assertEqual(len(same_name), 2)
            self.assertNotEqual(same_name[0]["path"], same_name[1]["path"])

    def test_country_navigation_is_safe_before_tilda_and_enables_only_verified_pages(self):
        expected = [
            {"geo_country": ["Россия"]}, {"geo_country": ["Кипр"]},
            {"geo_country": ["Турция"]}, {"geo_country": ["ОАЭ"], "geo_city": ["Дубай"]},
            {"geo_country": ["Испания"]},
        ]
        with patch.object(C, "PUBLISHED_COUNTRY_PAGES", frozenset()):
            urls = [a["href"] for a in Document(templates.country_links()).tags("a")]
            self.assertEqual(len(urls), len(expected))
            for url, filters in zip(urls, expected):
                parsed = urlsplit(url)
                self.assertEqual(parsed.path, "/")
                self.assertTrue(parsed.fragment.startswith("catalog?"))
                self.assertEqual(parse_qs(parsed.fragment.split("?", 1)[1]), filters)
            with built(inventory()) as (root, _):
                unpublished_urls = {C.MAIN_SITE + path for path in C.COUNTRY_PAGES.values()}
                for page in (root / "dist").rglob("*.html"):
                    hrefs = {a.get("href") for a in Document(page.read_text()).tags("a")}
                    self.assertFalse(hrefs & unpublished_urls, str(page))
        # Partial publication enables just that exact path, without guessing
        # whether the other three Tilda pages have been created yet.
        with patch.object(C, "PUBLISHED_COUNTRY_PAGES", frozenset({"/cyprus"})):
            urls = [a["href"] for a in Document(templates.country_links()).tags("a")]
            self.assertEqual(urls[1], C.MAIN_SITE + "/cyprus")
            self.assertTrue(all("/#catalog?" in url for i, url in enumerate(urls) if i != 1))
        with patch.object(C, "PUBLISHED_COUNTRY_PAGES", frozenset(C.COUNTRY_PAGES.values())):
            urls = [a["href"] for a in Document(templates.country_links()).tags("a")]
            self.assertEqual(urls[1:], [C.MAIN_SITE + path for path in C.COUNTRY_PAGES.values()])

    def test_chronology_in_hub_regional_lists_landings_and_geography(self):
        rows = inventory()
        with built(rows) as (root, _):
            history = paths_for(root)
            expected = [history[o["id"]] for o in newest_first([build.normalize(r) for r in rows if r["published"]])]
            self.assertEqual(Document(page_text(root, "/")).card_links(), expected)
            regional = [history["syntheticrunew2"], history["syntheticruold1"]]
            self.assertEqual(Document(page_text(root, "/kvartiry/")).card_links(), regional)
            self.assertEqual(Document(page_text(root, "/lp/podbor-kvartir/")).card_links("offer"), [C.SITE_BASE + p for p in regional])
            feed = json.loads((root / "dist/geografiya/cities.json").read_text())
            spain = next(x["path"] for x in feed["kvartiry"] if x["city"] == "Барселона")
            self.assertEqual(Document(page_text(root, spain)).card_links(), [history["synthetic" + x] for x in ("spain6", "spusd7", "spunk8")])
            # Editing an old record never promotes it through its updated field.
            self.assertEqual(expected[-1], history["syntheticruold1"])

    def test_publication_and_legacy_dates_are_truthful_in_html_and_schema(self):
        with built(inventory()) as (root, _):
            history = paths_for(root)
            old = page_text(root, history["syntheticruold1"])
            new = page_text(root, history["syntheticrunew2"])
            self.assertIn("Добавлено: 01.10.2026", old)
            self.assertIn("Опубликовано: 25.11.2026", new)
            old_ld, new_ld = Document(old).structured[0], Document(new).structured[0]
            self.assertNotIn("datePosted", old_ld)
            self.assertEqual(old_ld["dateCreated"], "2026-10-01T10:00:00Z")
            self.assertEqual(new_ld["datePosted"], "2026-11-25T09:00:00Z")
            self.assertIn("Добавлено: 01.10.2026", page_text(root, "/lp/podbor-kvartir/"))
            self.assertIn("Опубликовано: 25.11.2026", page_text(root, "/lp/podbor-kvartir/"))
        missing = build.normalize(record("nodate", created="", published_at="invalid"))
        self.assertEqual(build.listing_date_html(missing), "")

    def test_currency_contract_in_metadata_cards_and_price_tables(self):
        unsupported = record("badcur", country="RU", currency="XYZ", price=1234567.89)
        normalized = build.normalize(unsupported)
        self.assertIsNone(normalized["currency"])
        self.assertIsNone(currency_for(normalized))
        self.assertIsNone(currency_for(build.normalize(normalized)))
        with built(inventory() + [unsupported]) as (root, _):
            history = paths_for(root)
            for suffix, currency, amount in [("ruold1", "RUB", 1200000), ("cypru3", "EUR", 285000.75), ("turke4", "TRY", 5000000), ("duba05", "AED", 1450000), ("spusd7", "USD", 600000)]:
                html = page_text(root, history["synthetic" + suffix])
                listing = Document(html).structured[0]
                self.assertEqual(listing["offers"]["priceCurrency"], currency)
                self.assertEqual(listing["offers"]["price"], amount)
                self.assertIn(C.fmt_price_plain(amount, currency), html)
            unknown = page_text(root, history["syntheticspunk8"])
            self.assertIn("900 000 · валюта уточняется", unknown)
            self.assertNotIn("offers", Document(unknown).structured[0])
            invalid_currency_page = page_text(root, history[unsupported["id"]])
            self.assertIn("1 234 567,89 · валюта уточняется", invalid_currency_page)
            self.assertNotIn("offers", Document(invalid_currency_page).structured[0])
            self.assertIn("1 234 567,89 · валюта уточняется", page_text(root, "/lp/podbor-kvartir/"))
            home = page_text(root, "/")
            self.assertNotIn("цены от", home)
            self.assertNotIn('<div class="l">Цена от</div>', home)
            feed = json.loads((root / "dist/geografiya/cities.json").read_text())
            spain = next(x["path"] for x in feed["kvartiry"] if x["city"] == "Барселона")
            tables = Document(page_text(root, spain)).tags("section", **{"class": "room-prices"})
            self.assertEqual({t["data-currency"] for t in tables}, {"EUR", "USD"})
        self.assertIsNone(build.normalize(record("uncoun", region="", country=""))["currency"])
        self.assertIsNone(build.normalize(record("badcur", currency="XYZ"))["currency"])
        self.assertEqual(build.normalize(record("rubru1", country="RU"))["currency"], "RUB")

    def test_video_urls_controls_poster_and_hostile_values(self):
        bad = ["javascript:harmless", "//example.invalid/test.mp4", "https://example.invalid/test.mp4", "../test.mp4", "x.svg", "http://[", "x.mp4?fake=1", "x\\test.mp4"]
        row = record("videos", country="CY", region="Лимасол", currency="EUR", videos=bad + ["обзор квартиры.mp4", "tour.webm", "third.MP4", "fourth.mp4"])
        with built([row]) as (root, _):
            doc = Document(page_text(root, paths_for(root)[row["id"]]))
            players = doc.tags("video")
            self.assertEqual(len(players), 3)
            for player in players:
                self.assertIn("controls", player)
                self.assertIn("playsinline", player)
                self.assertEqual(player["preload"], "metadata")
                self.assertNotIn("autoplay", player)
                self.assertTrue(player["poster"].endswith("/photo.jpg"))
            sources = doc.tags("source")
            self.assertEqual([s["type"] for s in sources], ["video/mp4", "video/webm", "video/mp4"])
            self.assertTrue(all(s["src"].startswith(C.PB_URL + "/api/files/listings/" + row["id"] + "/") for s in sources))
            self.assertIn("%20", sources[0]["src"])
            self.assertTrue(unquote(sources[0]["src"]).endswith("/обзор квартиры.mp4"))
        plain = build.normalize(record("novide", videos=[]))
        plain["url"] = "/obekt/plain-novide/"
        self.assertEqual(Document(build.render_object(plain, C.FALLBACK_SETTINGS, [])).tags("video"), [])

    def test_benign_markup_does_not_break_jsonld_or_visible_text(self):
        marker = '</script><p id="audit-boundary-marker">Безвредная проверка</p>'
        row = record("marker", title=marker, description=marker, residential_complex=marker,
                     published_at="2026-11-25T12:00:00Z")
        with built([row]) as (root, _):
            for path in [paths_for(root)[row["id"]], "/", "/kvartiry/", "/lp/podbor-kvartir/"]:
                html = page_text(root, path)
                doc = Document(html)
                self.assertFalse([attrs for _, attrs in doc.elements if attrs.get("id") == "audit-boundary-marker"])
                self.assertTrue(doc.structured)
                if path != "/":  # The hub schema contains no listing text.
                    self.assertIn("\\u003c", html)
            self.assertEqual(Document(page_text(root, paths_for(root)[row["id"]])).structured[0]["name"], marker)

    def test_title_edit_retains_every_existing_object_url(self):
        rows = inventory()
        retained = {rows[0]["id"]: "/obekt/already-published-ruold1/"}
        with built(rows, retained) as (root, log):
            before = paths_for(root)
            for row in rows:
                row["title"] = "Изменённый заголовок " + row["id"]
            with redirect_stdout(log):
                build.build()
            self.assertEqual(paths_for(root), before)
            for path in before.values():
                doc = Document(page_text(root, path))
                self.assertEqual(doc.tags("link", rel="canonical")[0]["href"], C.SITE_BASE + path)
            turkey = build.normalize(next(r for r in rows if r["id"] == "syntheticturke4"))
            self.assertEqual(turkey["country"], "Турция")
            self.assertEqual(turkey["region"], "Турция")
        # The checked-in registry is the release's pinned main history, including
        # paths added after the original international candidate was prepared.
        # Only IDs/URLs are used; these are synthetic objects with changed titles.
        published_paths = json.loads((Path(__file__).resolve().parents[1] /
                                     ".horizontriel-seo-stable-urls.json").read_text())["paths"]
        renamed = [build.normalize(record("renamed", id=rid, title="Новый заголовок " + rid))
                   for rid in published_paths]
        retained_paths = build.htseo_assign_stable_urls(renamed, dict(published_paths))
        self.assertEqual(retained_paths, published_paths)
        self.assertEqual({obj["id"]: obj["url"] for obj in renamed}, published_paths)

    def test_fetch_requests_public_contract_fields_and_paginates(self):
        responses = [{"items": [record("page01")], "totalPages": 2}, {"items": [record("page02")], "totalPages": 2}]
        with patch.object(build, "_get_json", side_effect=responses) as get:
            self.assertEqual(len(build.fetch_listings()), 2)
        for call in get.call_args_list:
            query = parse_qs(urlsplit(call.args[0]).query)
            fields = set(query["fields"][0].split(","))
            self.assertTrue({"country", "currency", "published_at", "videos", "created"} <= fields)
            self.assertEqual(query["filter"], ["(published=true)"])
            self.assertEqual(query["sort"], ["-created,id"])
            self.assertNotIn("owner_phone1", fields)

    def test_moscow_calendar_day_and_deterministic_utc_order(self):
        rows = [record("equalb", published_at="2026-11-25T22:30:00Z"),
                record("equala", published_at="2026-11-26T01:30:00+03:00"),
                record("older0", created="2026-11-25T22:29:59Z", published_at="bad-date"),
                record("nodate", created="", published_at="")]
        with built(rows) as (root, _):
            history = paths_for(root)
            expected = [history["synthetic" + x] for x in ("equala", "equalb", "older0", "nodate")]
            self.assertEqual(Document(page_text(root, "/kvartiry/")).card_links(), expected)
            for path in ["/kvartiry/", "/lp/podbor-kvartir/", history["syntheticequala"]]:
                self.assertIn("Опубликовано: 26.11.2026", page_text(root, path))
            self.assertIn("Добавлено: 26.11.2026", page_text(root, history["syntheticolder0"]))
            listing = Document(page_text(root, history["syntheticequala"])).structured[0]
            self.assertEqual(listing["datePosted"], "2026-11-25T22:30:00Z")

    def test_full_build_includes_pinned_map_dependencies_and_licenses(self):
        with built([record("assets")]) as (root, _):
            vendor = root / "dist/assets/vendor"
            manifest = json.loads((vendor / "manifest.json").read_text())
            self.assertEqual(len(manifest), 12)
            for item in manifest:
                data = (vendor / item["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            for image in ("layers.png", "layers-2x.png", "marker-icon.png", "marker-icon-2x.png", "marker-shadow.png"):
                self.assertTrue((vendor / "leaflet-1.9.4/images" / image).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
