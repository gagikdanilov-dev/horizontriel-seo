"""Build the crawlable city directory and its matching Tilda feed from published listings."""
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlencode

import config as C
from templates import breadcrumbs_html, card, esc, esc_attr, page


DIRECTORY = "/geografiya/"
ALIASES = {key.casefold(): key for key in C.TYPE_META}
ALIASES.update({
    "квартиры": "Квартира", "дома": "Дом", "коттедж": "Дом",
    "участок": "Земля", "земельный участок": "Земля",
    "коммерческая недвижимость": "Коммерция", "коммерческая": "Коммерция",
})


def listing_types(obj):
    extra = obj.get("additional_types") or []
    values = [obj.get("type"), *(extra if isinstance(extra, list) else [extra])]
    return {ALIASES[value.strip().casefold()] for value in values
            if isinstance(value, str) and value.strip().casefold() in ALIASES}


def location(obj):
    def clean(value):
        return " ".join(str(value or "").split())

    country = clean(obj.get("country"))
    region = clean(obj.get("region"))
    if country.casefold() in {"ru", "rus", "россия", "russia", "российская федерация"}:
        country = "Россия"
    if not country and region.casefold() == C.SEO_REGION.casefold():
        country = "Россия"
    city = clean(obj.get("city"))
    if country == "Россия" and region.casefold() == C.SEO_REGION.casefold():
        if city.casefold() in {"пос. иноземцево", "посёлок иноземцево", "поселок иноземцево"}:
            city = "Иноземцево"
    return country, region, city


def in_home_region(obj):
    country, region, _ = location(obj)
    return country == "Россия" and region.casefold() == C.SEO_REGION.casefold()


def catalog_jump(type_slug="", *, country=None, region=None, city=None):
    query = {key: value for key, value in (
        ("geo_country", country), ("geo_region", region), ("geo_city", city)
    ) if value is not None}
    if type_slug:
        query["type"] = type_slug
    href = C.MAIN_SITE + "/#catalog" + ("?" + urlencode(query) if query else "")
    return (
        '<div class="main-catalog-jump"><div class="txt">'
        f'<b>Открыть объекты в основном каталоге {esc(C.BRAND)}</b>'
        'Выбранные фильтры сохранятся при переходе.</div>'
        f'<a class="go" href="{esc_attr(href)}">Смотреть объекты →</a></div>'
    )


def build_directory(objects, local_paths, write_page, urls):
    # Keep different countries and regions distinct even when their city names match.
    groups = defaultdict(list)
    names = {}
    for obj in objects:
        place = location(obj)
        if not place[2]:
            continue
        identity = tuple(part.casefold() for part in place)
        names.setdefault(identity, place)
        for kind in listing_types(obj):
            groups[kind, identity].append(obj)

    feed = {}
    sections = []
    for kind, meta in C.TYPE_META.items():
        category = meta["slug"]
        entries = []
        for (item_kind, identity), rows in groups.items():
            if item_kind != kind:
                continue
            country, region, city = names[identity]
            area = " · ".join(dict.fromkeys(x for x in (country, region) if x))
            local_path = f'/gorod/{C.slugify(city)}/{category}/'
            # Use an existing regional URL only if it contains this exact collection.
            ids = {row["id"] for row in rows}
            if in_home_region(rows[0]) and local_paths.get(local_path) == ids:
                path = local_path
            else:
                digest = sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()[:16]
                slug = C.slugify(city)[:60] or "city"
                path = f'{DIRECTORY}{slug}-{digest}/{category}/'
                heading = " — ".join(x for x in (meta["plural"], city, area) if x)
                intro = f'Опубликованные предложения. Объектов в подборке: {len(rows)}.'
                body = (breadcrumbs_html([("География каталога", DIRECTORY), (city, None)])
                        + '<div class="wrap section"><h1>' + esc(heading) + '</h1><p>'
                        + esc(intro) + '</p>'
                        + catalog_jump(category, country=country, region=region, city=city)
                        + '<div class="grid">'
                        + "".join(card(row) for row in rows) + '</div></div>')
                write_page(path, page(title=heading + " | " + C.BRAND, description=intro + " " + heading,
                                      canonical=C.SITE_BASE + path, body=body), urls)
            entries.append({"area": area, "city": city, "path": path, "count": len(rows)})
        entries.sort(key=lambda e: (e["area"].casefold(), e["city"].casefold(), e["path"]))
        feed[category] = entries
        # Keep the section anchor available even when its final listing is removed.
        section = [f'<section id="{esc_attr(category)}"><h2>{esc(meta["plural"])}</h2>']
        by_area = defaultdict(list)
        for item in entries:
            by_area[item["area"]].append(item)
        for area, items in by_area.items():
            section.append(f'<h3>{esc(area)}</h3>' if area else '')
            section.append('<div class="pills">')
            for item in items:
                section.append(f'<a class="pill" href="{esc_attr(item["path"])}">'
                               f'{esc(item["city"])} · {item["count"]}</a>')
            section.append('</div>')
        if not entries:
            section.append('<p>Пока нет опубликованных предложений с указанным городом.</p>')
        sections.append(''.join(section) + '</section>')
    title = "Недвижимость по городам и регионам"
    body = (breadcrumbs_html([("Каталог", "/"), ("География", None)])
            + '<main class="wrap section"><h1>' + title + '</h1>'
            + ''.join(sections) + '</main>')
    write_page(DIRECTORY, page(title=title + " | " + C.BRAND,
                               description="Выберите тип недвижимости и город, в котором есть опубликованные объекты.",
                               canonical=C.SITE_BASE + DIRECTORY, body=body), urls, index=any(feed.values()))
    (Path(C.OUT_DIR) / "geografiya" / "cities.json").write_text(
        json.dumps(feed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
