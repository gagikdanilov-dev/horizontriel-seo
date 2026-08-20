#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор статических SEO-страниц HorizonTriel.

SEO-стратегия:
  • главный брендовый сайт: https://horizontriel.com/
  • catalog.horizontriel.com/ — рабочий каталог, но его КОРЕНЬ noindex
  • индексируются страницы объектов, типов, городов и региона
  • SEO-география: Ставропольский край / КМВ
  • в sitemap НЕ добавляется корень catalog.horizontriel.com/

Запуск локально на тестовых данных:
    python build.py --sample

Боевой запуск:
    python build.py
"""

import os
import sys
import json
import shutil
import urllib.request
from datetime import date
from urllib.parse import urlparse, quote

import config as C
from config import (
    slugify,
    type_meta,
    city_prep,
    region_prep,
    plural_ru,
    fmt_price_plain,
)
from templates import (
    esc,
    esc_attr,
    page,
    card,
    breadcrumbs_html,
    footer,
)

SAMPLE = "--sample" in sys.argv or os.environ.get("SAMPLE") == "1"


# ─────────────────────────── загрузка данных ───────────────────────────

def _get_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "horizontriel-seo/2.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_listings():
    fields = (
        "id,title,type,tag,region,city,address,description,residential_complex,"
        "completion_date,promotion,price,area,living_area,kitchen_area,year,floor,"
        "floors,rooms,land,land_purpose,plot_frontage,wall_material,communications,"
        "condition,deal,published,featured,sort_order,features,images,floorplans,"
        "created,updated"
    )
    url = (
        f"{C.PB_URL}/api/collections/{C.PB_COLLECTION}/records"
        f"?filter=(published=true)&sort=sort_order,created"
        f"&perPage=500&fields={quote(fields)}"
    )
    data = _get_json(url)
    return data.get("items") or data.get("records") or []


def fetch_settings():
    try:
        d = _get_json(
            f"{C.PB_URL}/api/collections/{C.PB_SETTINGS}/records"
            "?perPage=1&sort=created"
        )
        items = d.get("items") or []
        rec = items[0] if items else {}
    except Exception:
        rec = {}

    return {
        "tel": rec.get("tel") or C.FALLBACK_SETTINGS["tel"],
        "wa": rec.get("wa") or C.FALLBACK_SETTINGS["wa"],
        "tg": rec.get("tg") or C.FALLBACK_SETTINGS["tg"],
        "max": (
            rec.get("max_url")
            or rec.get("max")
            or C.FALLBACK_SETTINGS["max"]
        ),
        "email": rec.get("email") or C.FALLBACK_SETTINGS["email"],
    }


# ─────────────────────────── нормализация ───────────────────────────

def _files_to_urls(rec_id, raw):
    if not raw:
        return []

    arr = raw if isinstance(raw, list) else [raw]
    out = []

    for f in arr:
        name = f.get("name") if isinstance(f, dict) else f

        if not name:
            continue

        if isinstance(name, str) and name.startswith("http"):
            out.append(name)
        else:
            out.append(
                f"{C.PB_URL}/api/files/{C.PB_COLLECTION}/{rec_id}/{name}"
            )

    return out


def _norm_feature(s):
    if not s:
        return ""

    if s == "Вид на воду":
        return "Вид на море"

    if s == "Ипотека одобрена":
        return "Ипотека"

    return s


def normalize(r):
    feats_raw = r.get("features")
    feats = (
        feats_raw
        if isinstance(feats_raw, list)
        else ([feats_raw] if feats_raw else [])
    )

    return {
        "id": r.get("id"),
        "title": r.get("title"),
        "type": r.get("type"),
        "tag": r.get("tag"),
        "region": r.get("region"),
        "city": r.get("city"),
        "address": r.get("address"),
        "desc": r.get("description"),
        "residential_complex": r.get("residential_complex"),
        "completion_date": r.get("completion_date"),
        "promotion": r.get("promotion"),
        "price": int(r.get("price") or 0),
        "area": r.get("area"),
        "living_area": r.get("living_area"),
        "kitchen_area": r.get("kitchen_area"),
        "year": r.get("year"),
        "floor": r.get("floor"),
        "floors": r.get("floors"),
        "rooms": r.get("rooms"),
        "land": r.get("land"),
        "land_purpose": r.get("land_purpose"),
        "plot_frontage": r.get("plot_frontage"),
        "wall_material": r.get("wall_material"),
        "communications": r.get("communications"),
        "condition": r.get("condition"),
        "deal": r.get("deal"),
        "featured": r.get("featured"),
        "order": r.get("sort_order"),
        "features": [_norm_feature(f) for f in feats if f],
        "images": _files_to_urls(r.get("id"), r.get("images")),
        "floorplans": _files_to_urls(
            r.get("id"),
            r.get("floorplans") or r.get("floorplan") or r.get("plans")
        ),
        "createdAt": r.get("created"),
        "updatedAt": r.get("updated"),
    }


def obj_url(o):
    base = slugify(
        o.get("title") or o.get("type") or "obekt"
    ) or "obekt"
    sid = (o.get("id") or "")[-6:]
    return f"/obekt/{base}-{sid}/"


# ─────────────────────────── помощники ───────────────────────────

def price_stats(objs):
    prices = [
        o["price"]
        for o in objs
        if o.get("price")
    ]

    areas = []
    for o in objs:
        value = o.get("area")
        if value in (None, ""):
            continue
        try:
            areas.append(float(value))
        except Exception:
            pass

    return {
        "n": len(objs),
        "min": min(prices) if prices else 0,
        "max": max(prices) if prices else 0,
        "avg_area": round(sum(areas) / len(areas)) if areas else 0,
    }


def facts_row(st, _genpl=""):
    cells = []

    word = plural_ru(
        st["n"],
        "объект",
        "объекта",
        "объектов"
    )

    cells.append(
        '<div class="fact">'
        f'<div class="n">{st["n"]}</div>'
        f'<div class="l">{word} в подборке</div>'
        '</div>'
    )

    if st["min"]:
        cells.append(
            '<div class="fact">'
            f'<div class="n">{esc(fmt_price_plain(st["min"]))}</div>'
            '<div class="l">Цена от</div>'
            '</div>'
        )

    if st["avg_area"]:
        cells.append(
            '<div class="fact">'
            f'<div class="n">{st["avg_area"]} м²</div>'
            '<div class="l">Средняя площадь</div>'
            '</div>'
        )

    return '<div class="facts">' + "".join(cells) + "</div>"


def faq_html(qas):
    if not qas:
        return ""

    items = "".join(
        f'<details><summary>{esc(q)}</summary>'
        f'<div class="a">{esc(a)}</div></details>'
        for q, a in qas
    )

    return (
        '<div class="wrap section">'
        '<div class="eyebrow">Частые вопросы</div>'
        f'<div class="faq">{items}</div>'
        '</div>'
    )


def related_pills(links):
    if not links:
        return ""

    pills = "".join(
        f'<a class="pill" href="{esc_attr(u)}">{esc(l)}</a>'
        for l, u in links
    )

    return (
        '<div class="wrap">'
        f'<div class="pills">{pills}</div>'
        '</div>'
    )


def strip_tags(s):
    import re
    return re.sub(r"<[^>]+>", "", str(s)).strip()


# ─────────────────────────── страница объекта ───────────────────────────

def render_object(o, settings, similar):
    url_abs = C.SITE_BASE + o["url"]
    tmeta = type_meta(o.get("type"))

    place = " · ".join(
        [
            x
            for x in (
                o.get("region"),
                o.get("city")
            )
            if x
        ]
    )

    title_bits = [
        o.get("title") or "Объект недвижимости"
    ]

    loc = ", ".join(
        [
            x
            for x in (
                o.get("city"),
                o.get("region")
            )
            if x
        ]
    )

    if loc:
        title_bits.append(loc)

    if o.get("area"):
        title_bits.append(f'{o["area"]} м²')

    if o.get("price"):
        title_bits.append(
            fmt_price_plain(o["price"])
        )

    seo_title = (
        " — ".join(title_bits)
        + f" | {C.BRAND}"
    )

    d_bits = [
        f'{o.get("deal") or "Продажа"}: '
        f'{o.get("title") or "объект недвижимости"}'
    ]

    dl = ", ".join(
        [
            x
            for x in (
                o.get("region"),
                o.get("city"),
                o.get("address")
            )
            if x
        ]
    )

    if dl:
        d_bits.append(dl)

    if o.get("area"):
        d_bits.append(f'{o["area"]} м²')

    if o.get("rooms"):
        d_bits.append(f'{o["rooms"]} комн.')

    if o.get("price"):
        d_bits.append(
            fmt_price_plain(o["price"])
        )

    seo_desc = ". ".join(d_bits)[:240]

    # Галерея
    imgs = o.get("images") or []
    plans = o.get("floorplans") or []

    gal = '<div class="gallery">'

    if imgs:
        gal += (
            f'<div class="gal-main">'
            f'<img src="{esc_attr(imgs[0])}" '
            f'alt="{esc_attr(o.get("title"))}">'
            '</div>'
        )

        if len(imgs) > 1:
            gal += (
                '<div class="gal-thumbs">'
                + "".join(
                    f'<img src="{esc_attr(u)}" '
                    f'alt="{esc_attr(o.get("title"))} — фото {i + 2}" '
                    'loading="lazy">'
                    for i, u in enumerate(imgs[1:9])
                )
                + "</div>"
            )

    if plans:
        gal += '<div class="plans-lbl">Планировка</div>'
        gal += (
            '<div class="gal-thumbs">'
            + "".join(
                f'<img src="{esc_attr(u)}" '
                f'alt="{esc_attr(o.get("title"))} — планировка {i + 1}" '
                'loading="lazy">'
                for i, u in enumerate(plans[:6])
            )
            + "</div>"
        )

    if not imgs and not plans:
        gal += (
            '<div class="gal-main card-noimg">'
            '<span>Фото готовится</span>'
            '</div>'
        )

    gal += "</div>"

    # Параметры
    params_list = []

    def add(label, value):
        if value not in (None, "", 0):
            params_list.append((label, value))

    add("Регион", o.get("region"))
    add("Город", o.get("city"))
    add("ЖК", o.get("residential_complex"))
    add("Срок сдачи", o.get("completion_date"))
    add(
        "Общая площадь",
        f'{o["area"]} м²'
        if o.get("area")
        else None
    )
    add(
        "Жилая площадь",
        f'{o["living_area"]} м²'
        if o.get("living_area")
        else None
    )
    add(
        "Площадь кухни",
        f'{o["kitchen_area"]} м²'
        if o.get("kitchen_area")
        else None
    )
    add("Комнат", o.get("rooms"))

    if o.get("floor") and o.get("floors"):
        add(
            "Этаж",
            f'{o["floor"]} из {o["floors"]}'
        )
    elif o.get("floor"):
        add("Этаж", o.get("floor"))

    add("Год", o.get("year"))
    add(
        "Участок",
        f'{o["land"]} сот.'
        if o.get("land")
        else None
    )
    add(
        "Назначение земли",
        o.get("land_purpose")
    )
    add(
        "Фасад участка",
        f'{o["plot_frontage"]} м'
        if o.get("plot_frontage")
        else None
    )
    add(
        "Материал стен",
        o.get("wall_material")
    )
    add(
        "Коммуникации",
        o.get("communications")
    )
    add(
        "Состояние",
        o.get("condition")
    )
    add("Тип", o.get("type"))
    add("Адрес", o.get("address"))

    params = (
        '<div class="params">'
        + "".join(
            '<div class="p">'
            f'<div class="plbl">{esc(label)}</div>'
            f'<div class="pval">{esc(value)}</div>'
            '</div>'
            for label, value in params_list
        )
        + "</div>"
    )

    promo = ""
    if o.get("promotion"):
        promo = (
            '<div class="promo">'
            '<b>Акция / спецпредложение</b>'
            f'{esc(o["promotion"])}'
            '</div>'
        )

    desc = (
        f'<div class="desc">{esc(o["desc"])}</div>'
        if o.get("desc")
        else ""
    )

    feats = ""
    if o.get("features"):
        chips = "".join(
            f'<span class="feat">{esc(f)}</span>'
            for f in o["features"]
        )

        feats = (
            '<div class="feats-lbl">Особенности</div>'
            f'<div class="feats">{chips}</div>'
        )

    # CTA
    wa_msg = quote(
        f'Здравствуйте! Интересует: '
        f'{o.get("title") or ""}'
        + (
            f' ({place})'
            if place
            else ""
        )
        + f' — {fmt_price_plain(o.get("price"))}\n'
        + url_abs
    )

    tel_href = "".join(
        c
        for c in settings["tel"]
        if c.isdigit() or c == "+"
    )

    cta = (
        '<div class="cta">'
        f'<a class="btn btn-wa" '
        f'href="https://wa.me/{esc_attr(settings["wa"])}?text={wa_msg}" '
        'target="_blank" rel="noopener">WhatsApp</a>'
        f'<a class="btn btn-tg" '
        f'href="{esc_attr(settings["tg"])}" '
        'target="_blank" rel="noopener">Telegram</a>'
        + (
            f'<a class="btn btn-max" '
            f'href="{esc_attr(settings["max"])}" '
            'target="_blank" rel="noopener">MAX</a>'
            if settings.get("max")
            else ""
        )
        + f'<a class="btn btn-call" '
        f'href="tel:{esc_attr(tel_href)}">Позвонить</a>'
        '</div>'
    )

    price_row = (
        '<div class="price-row">'
        f'<div class="price-big">'
        f'{esc(fmt_price_plain(o.get("price")))}'
        '</div>'
        + (
            f'<span class="deal">'
            f'{esc(o.get("deal"))}'
            '</span>'
            if o.get("deal")
            else ""
        )
        + "</div>"
    )

    crumbs = [
        (
            "Каталог",
            C.SITE_BASE + "/"
        )
    ]

    if o.get("city"):
        crumbs.append(
            (
                o["city"],
                C.SITE_BASE
                + f'/gorod/{slugify(o["city"])}/'
            )
        )

    if o.get("type"):
        crumbs.append(
            (
                tmeta["plural"],
                C.SITE_BASE
                + f'/{tmeta["slug"]}/'
            )
        )

    crumbs.append(
        (
            o.get("title") or "Объект",
            None
        )
    )

    similar_html = ""
    if similar:
        similar_html = (
            '<div class="wrap section">'
            '<h2>Похожие объекты</h2>'
            '<div class="grid">'
            + "".join(
                card(s)
                for s in similar[:4]
            )
            + "</div></div>"
        )

    body = (
        breadcrumbs_html(crumbs)
        + '<div class="wrap section">'
        '<div class="obj">'
        + gal
        + '<div class="obj-side">'
        + (
            f'<div class="place">{esc(place)}</div>'
            if place
            else ""
        )
        + f'<h1>{esc(o.get("title") or "Объект недвижимости")}</h1>'
        + price_row
        + params
        + promo
        + desc
        + feats
        + cta
        + '</div></div></div>'
        + similar_html
        + footer(
            settings,
            _hub_seo_links_cache
        )
    )

    ld_listing = {
        "@context": "https://schema.org",
        "@type": "RealEstateListing",
        "name": (
            o.get("title")
            or "Объект недвижимости"
        ),
        "description": (
            o.get("desc")
            or seo_desc
        ),
        "url": url_abs,
        "datePosted": (
            str(o.get("createdAt"))[:10]
            if o.get("createdAt")
            else None
        ),
        "image": (
            o.get("images")
            or []
        )[:12],
        "address": {
            "@type": "PostalAddress",
            "addressCountry": "RU",
            "addressRegion": (
                o.get("region")
                or ""
            ),
            "addressLocality": (
                o.get("city")
                or ""
            ),
            "streetAddress": (
                o.get("address")
                or ""
            ),
        },
        "offers": {
            "@type": "Offer",
            "priceCurrency": "RUB",
            "price": (
                o.get("price")
                or None
            ),
            "availability": (
                "https://schema.org/InStock"
            ),
            "url": url_abs,
        },
    }

    ld_bc = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": name,
                "item": (
                    url
                    or url_abs
                ),
            }
            for i, (name, url)
            in enumerate(crumbs)
        ],
    }

    og_img = (
        o.get("images")
        or [None]
    )[0]

    return page(
        title=seo_title,
        description=seo_desc,
        canonical=url_abs,
        body=body,
        jsonld=[
            ld_listing,
            ld_bc
        ],
        og_image=og_img,
    )


# ─────────────────────────── кластерные страницы ───────────────────────────

_hub_seo_links_cache = []


def contact_cta(settings):
    tel_href = "".join(
        c
        for c in settings["tel"]
        if c.isdigit() or c == "+"
    )

    return (
        '<div class="cta">'
        f'<a class="btn btn-wa" '
        f'href="https://wa.me/{esc_attr(settings["wa"])}" '
        'target="_blank" rel="noopener">WhatsApp</a>'
        f'<a class="btn btn-tg" '
        f'href="{esc_attr(settings["tg"])}" '
        'target="_blank" rel="noopener">Telegram</a>'
        + (
            f'<a class="btn btn-max" '
            f'href="{esc_attr(settings["max"])}" '
            'target="_blank" rel="noopener">MAX</a>'
            if settings.get("max")
            else ""
        )
        + f'<a class="btn btn-call" '
        f'href="tel:{esc_attr(tel_href)}">Позвонить</a>'
        '</div>'
    )


def render_cluster(
    *,
    kind,
    key,
    objs,
    settings,
    h1,
    seo_title,
    seo_desc,
    intro_paras,
    crumbs,
    related,
    faq,
    path,
    robots="index, follow, max-image-preview:large",
):
    url_abs = C.SITE_BASE + path

    if not objs:
        body = (
            breadcrumbs_html(crumbs)
            + '<div class="wrap section">'
            f'<div class="eyebrow">'
            f'Каталог · {esc(kind_label(kind))}'
            '</div>'
            f'<h1>{h1}</h1>'
            '<div class="prose">'
            '<p>В этой категории пока нет опубликованных объектов. '
            'Оставьте заявку — подберём подходящий вариант '
            'в Ставропольском крае под ваш бюджет и цель.</p>'
            '</div>'
            + contact_cta(settings)
            + related_pills(related)
            + footer(
                settings,
                _hub_seo_links_cache
            )
        )

        ld = [
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": strip_tags(h1),
                "url": url_abs,
                "inLanguage": "ru-RU",
            },
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i + 1,
                        "name": n,
                        "item": (
                            u
                            or url_abs
                        ),
                    }
                    for i, (n, u)
                    in enumerate(crumbs)
                ],
            },
        ]

        return page(
            title=seo_title,
            description=seo_desc,
            canonical=url_abs,
            body=body,
            jsonld=ld,
            robots=robots,
        )

    st = price_stats(objs)

    grid = (
        '<div class="grid">'
        + "".join(
            card(o)
            for o in objs
        )
        + "</div>"
    )

    prose = ""
    if intro_paras:
        prose = (
            '<div class="prose">'
            + "".join(
                f"<p>{esc(p)}</p>"
                for p in intro_paras
            )
            + "</div>"
        )

    body = (
        breadcrumbs_html(crumbs)
        + '<div class="wrap section">'
        f'<div class="eyebrow">'
        f'Каталог · {esc(kind_label(kind))}'
        '</div>'
        f'<h1>{h1}</h1>'
        + facts_row(st)
        + prose
        + grid
        + "</div>"
        + related_pills(related)
        + faq_html(faq)
        + footer(
            settings,
            _hub_seo_links_cache
        )
    )

    ld_items = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": strip_tags(h1),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": (
                    C.SITE_BASE
                    + o["url"]
                ),
                "name": (
                    o.get("title")
                    or "Объект недвижимости"
                ),
            }
            for i, o
            in enumerate(objs[:50])
        ],
    }

    ld_page = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": strip_tags(h1),
        "url": url_abs,
        "inLanguage": "ru-RU",
    }

    ld_bc = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": n,
                "item": (
                    u
                    or url_abs
                ),
            }
            for i, (n, u)
            in enumerate(crumbs)
        ],
    }

    ld = [
        ld_page,
        ld_items,
        ld_bc
    ]

    if faq:
        ld.append(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": strip_tags(q),
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": strip_tags(a),
                        },
                    }
                    for q, a in faq
                ],
            }
        )

    og_img = next(
        (
            o["images"][0]
            for o in objs
            if o.get("images")
        ),
        None,
    )

    return page(
        title=seo_title,
        description=seo_desc,
        canonical=url_abs,
        body=body,
        jsonld=ld,
        og_image=og_img,
        robots=robots,
    )


def kind_label(kind):
    return {
        "type": "По типу",
        "city": "По городу",
        "region": "По региону",
        "city_type": "Город и тип",
    }.get(
        kind,
        "Каталог"
    )


# ─────────────────────────── корень каталога ───────────────────────────

def render_hub(
    objs,
    by_type,
    by_city,
    by_region,
    settings
):
    """
    Корень catalog.horizontriel.com/ остаётся доступным людям,
    но НЕ индексируется Google и canonical указывает на главный сайт.
    """
    seo_title = (
        "Каталог недвижимости в Ставропольском крае"
        f" | {C.BRAND}"
    )

    seo_desc = (
        f"{C.BRAND} — каталог недвижимости "
        "в Ставропольском крае и на КМВ. "
        "Квартиры, дома, участки, гаражи и коммерческие объекты "
        "в Кисловодске, Пятигорске, Ессентуках, "
        "Железноводске, Минеральных Водах и Ставрополе."
    )

    st = price_stats(objs)

    def link_list(pairs):
        return (
            '<div class="pills">'
            + "".join(
                f'<a class="pill" href="{esc_attr(u)}">'
                f'{esc(label)} · {n}'
                '</a>'
                for label, u, n
                in pairs
            )
            + "</div>"
        )

    type_links = [
        (
            type_meta(t)["plural"],
            C.SITE_BASE
            + f'/{type_meta(t)["slug"]}/',
            len(v),
        )
        for t, v
        in sorted(
            by_type.items(),
            key=lambda kv: -len(kv[1])
        )
        if v
    ]

    city_links = [
        (
            city,
            C.SITE_BASE
            + f'/gorod/{slugify(city)}/',
            len(v),
        )
        for city, v
        in sorted(
            by_city.items(),
            key=lambda kv: -len(kv[1])
        )
        if v
    ]

    region_links = [
        (
            region,
            C.SITE_BASE
            + f'/region/{slugify(region)}/',
            len(v),
        )
        for region, v
        in sorted(
            by_region.items(),
            key=lambda kv: -len(kv[1])
        )
        if v
    ]

    featured = [
        o
        for o in objs
        if o.get("featured")
    ][:8] or objs[:8]

    feat_grid = (
        '<div class="grid">'
        + "".join(
            card(o)
            for o in featured
        )
        + "</div>"
    )

    intro = (
        '<div class="prose">'
        f'<p>{C.BRAND} помогает купить и продать недвижимость '
        'в Ставропольском крае и на Кавказских Минеральных Водах: '
        'квартиры, апартаменты, дома, коттеджи, таунхаусы, '
        'дуплексы, земельные участки, гаражи и коммерческие объекты. '
        'Основные направления — Кисловодск, Пятигорск, Ессентуки, '
        'Железноводск, Минеральные Воды и Ставрополь.</p>'
        f'<p>Сейчас в каталоге {st["n"]} '
        f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
        + (
            f', цены от {fmt_price_plain(st["min"])}'
            if st["min"]
            else ""
        )
        + '. Для каждого объекта доступна информация о характеристиках, '
        'стоимости и местоположении. Помогаем с проверкой, ипотекой '
        'и сопровождением сделки.</p>'
        '</div>'
    )

    body = (
        '<div class="wrap section">'
        '<div class="eyebrow">'
        'Каталог · Ставропольский край и КМВ'
        '</div>'
        '<h1>Недвижимость '
        '<em>в Ставропольском крае</em></h1>'
        + facts_row(st)
        + intro
        + '</div>'
        + '<div class="wrap section">'
        '<h2>По типу недвижимости</h2>'
        + link_list(type_links)
        + '</div>'
        + (
            '<div class="wrap section">'
            '<h2>По городам</h2>'
            + link_list(city_links)
            + '</div>'
            if city_links
            else ""
        )
        + (
            '<div class="wrap section">'
            '<h2>По региону</h2>'
            + link_list(region_links)
            + '</div>'
            if region_links
            else ""
        )
        + '<div class="wrap section">'
        '<h2>Избранные объекты</h2>'
        + feat_grid
        + '</div>'
        + footer(
            settings,
            _hub_seo_links_cache
        )
    )

    ld = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": C.BRAND,
            # Брендовый WebSite — основной домен, не поддомен каталога.
            "url": C.MAIN_SITE + "/",
            "inLanguage": "ru-RU",
        },
        {
            "@context": "https://schema.org",
            "@type": "RealEstateAgent",
            "name": C.BRAND,
            "url": C.MAIN_SITE + "/",
            "email": settings["email"],
            "telephone": settings["tel"],
            "areaServed": {
                "@type": "AdministrativeArea",
                "name": C.SEO_REGION,
            },
            "sameAs": [
                x
                for x in (
                    settings.get("tg"),
                    settings.get("max")
                )
                if x
            ],
        },
    ]

    og_img = next(
        (
            o["images"][0]
            for o in objs
            if o.get("images")
        ),
        None,
    )

    # КЛЮЧЕВО:
    # canonical -> основной сайт
    # robots -> noindex, follow
    return page(
        title=seo_title,
        description=seo_desc,
        canonical=C.MAIN_SITE + "/",
        body=body,
        jsonld=ld,
        og_image=og_img,
        robots="noindex, follow",
    )


# ─────────────────────────── запись файлов / sitemap ───────────────────────────

def write_page(
    path,
    html_str,
    urls,
    lastmod=None,
    index=True
):
    """
    path: '/gorod/kislovodsk/'.
    index=False -> файл создаётся, но URL не попадает в sitemap.
    """
    rel = path.strip("/")
    out = (
        os.path.join(
            C.OUT_DIR,
            rel
        )
        if rel
        else C.OUT_DIR
    )

    os.makedirs(
        out,
        exist_ok=True
    )

    with open(
        os.path.join(
            out,
            "index.html"
        ),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(html_str)

    if index:
        urls.append(
            (
                C.SITE_BASE
                + path,
                lastmod
                or date.today().isoformat(),
            )
        )


def write_sitemap(urls):
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for loc, lm in urls:
        body.append(
            '<url>'
            f'<loc>{esc(loc)}</loc>'
            f'<lastmod>{lm}</lastmod>'
            '</url>'
        )

    body.append("</urlset>")

    with open(
        os.path.join(
            C.OUT_DIR,
            "sitemap.xml"
        ),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(
            "\n".join(body)
        )


def write_robots():
    # Корень каталога намеренно НЕ запрещаем через robots.txt:
    # Google должен иметь возможность увидеть meta robots=noindex.
    txt = (
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {C.SITE_BASE}/sitemap.xml\n"
    )

    with open(
        os.path.join(
            C.OUT_DIR,
            "robots.txt"
        ),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(txt)


def write_cname():
    host = urlparse(
        C.SITE_BASE
    ).netloc

    if host:
        with open(
            os.path.join(
                C.OUT_DIR,
                "CNAME"
            ),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                host + "\n"
            )


# ─────────────────────────── SEO-тексты ───────────────────────────

def cluster_texts_city_type(
    city,
    ttype,
    objs
):
    tm = type_meta(ttype)
    cp = city_prep(city)
    st = price_stats(objs)

    h1 = (
        f'Купить {tm["gen"]} '
        f'{cp} — <em>{C.BRAND}</em>'
    )

    seo_title = (
        f'Купить {tm["gen"]} {cp} — '
        f'{st["n"]} '
        f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
        f' | {C.BRAND}'
    )

    seo_desc = (
        f'{tm["plural"]} {cp}: '
        f'{st["n"]} '
        f'{plural_ru(st["n"], "объект", "объекта", "объектов")} '
        'в каталоге'
        + (
            f', цены от {fmt_price_plain(st["min"])}'
            if st["min"]
            else ""
        )
        + '. Недвижимость Ставропольского края: '
        'подбор, проверка объекта, ипотека и сопровождение сделки.'
    )

    paras = [
        (
            f'Актуальные предложения по запросу '
            f'«{tm["plural"].lower()} {cp}». '
            f'В подборке {st["n"]} '
            f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
            + (
                f', цены начинаются от '
                f'{fmt_price_plain(st["min"])}'
                if st["min"]
                else ""
            )
            + (
                f', средняя площадь около '
                f'{st["avg_area"]} м²'
                if st["avg_area"]
                else ""
            )
            + '.'
        ),
        (
            'Проверяем документы, обременения, реальные расходы '
            f'и ликвидность объекта. Помогаем с ипотекой '
            f'и сопровождаем сделку {cp} до регистрации права.'
        ),
    ]

    faq = [
        (
            f'Какие цены на '
            f'{tm["plural"].lower()} {cp}?',
            (
                f'В каталоге {st["n"]} '
                f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
                + (
                    f', цены от {fmt_price_plain(st["min"])} '
                    f'до {fmt_price_plain(st["max"])}'
                    if st["min"]
                    else ""
                )
                + '. Точную стоимость подходящего объекта '
                'уточним при подборе.'
            ),
        ),
        (
            'Проверяете ли вы объект перед покупкой?',
            'Да. Проверяем документы, историю перехода прав, '
            'обременения и основные риски сделки.'
        ),
        (
            'Можно ли оформить ипотеку?',
            'Да. Помогаем подобрать ипотечную программу '
            'под конкретный объект и сопровождаем оформление.'
        ),
    ]

    return (
        h1,
        seo_title,
        seo_desc,
        paras,
        faq,
    )


def cluster_texts_city(
    city,
    objs
):
    cp = city_prep(city)
    st = price_stats(objs)

    h1 = (
        f'Недвижимость {cp} — '
        '<em>каталог</em>'
    )

    seo_title = (
        f'Недвижимость {cp} — '
        'квартиры, дома и участки'
        f' | {C.BRAND}'
    )

    seo_desc = (
        f'Каталог недвижимости {cp}, Ставропольский край: '
        'квартиры, дома, участки, гаражи и коммерческие объекты. '
        f'{st["n"]} '
        f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
        + (
            f', цены от {fmt_price_plain(st["min"])}'
            if st["min"]
            else ""
        )
        + '. Подбор, проверка, ипотека и сопровождение сделки.'
    )

    paras = [
        (
            f'Подбор и продажа недвижимости {cp}: '
            'квартиры, апартаменты, дома, таунхаусы, '
            'земельные участки, гаражи и коммерческие помещения. '
            f'В каталоге {st["n"]} '
            f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
            + (
                f', цены от {fmt_price_plain(st["min"])}'
                if st["min"]
                else ""
            )
            + '.'
        ),
        (
            f'Помогаем купить и продать объект {cp}: '
            'проверяем документы, оцениваем ликвидность, '
            'помогаем с ипотекой и сопровождаем сделку.'
        ),
    ]

    faq = [
        (
            f'Какую недвижимость можно купить {cp}?',
            'В каталоге есть квартиры, дома, таунхаусы, '
            'земельные участки, гаражи и коммерческие объекты.'
        ),
        (
            'Помогаете ли с продажей?',
            'Да. Оцениваем объект, готовим его к продаже, '
            'ищем покупателя и сопровождаем оформление.'
        ),
    ]

    return (
        h1,
        seo_title,
        seo_desc,
        paras,
        faq,
    )


def cluster_texts_region(
    region,
    objs
):
    rp = region_prep(region)
    st = price_stats(objs)

    h1 = (
        f'Недвижимость {rp}'
    )

    seo_title = (
        f'Недвижимость {rp} — '
        'квартиры, дома и участки'
        f' | {C.BRAND}'
    )

    seo_desc = (
        f'Недвижимость {rp}: '
        f'{st["n"]} '
        f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
        + (
            f', цены от {fmt_price_plain(st["min"])}'
            if st["min"]
            else ""
        )
        + '. Квартиры, дома, участки и коммерческие объекты. '
        'Подбор, проверка и сопровождение сделки.'
    )

    paras = [
        (
            f'Каталог недвижимости {rp}. '
            'Квартиры, дома, участки, гаражи и коммерческие объекты '
            'в Кисловодске, Пятигорске, Ессентуках, '
            'Железноводске, Минеральных Водах, Ставрополе '
            'и других населённых пунктах края. '
            f'В подборке {st["n"]} '
            f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
            + (
                f', цены от {fmt_price_plain(st["min"])}'
                if st["min"]
                else ""
            )
            + '.'
        ),
    ]

    return (
        h1,
        seo_title,
        seo_desc,
        paras,
        None,
    )


def cluster_texts_type(
    ttype,
    objs
):
    tm = type_meta(ttype)
    st = price_stats(objs)

    h1 = (
        f'{tm["plural"]} — '
        '<em>Ставропольский край</em>'
    )

    seo_title = (
        f'Купить {tm["gen"]} '
        'в Ставропольском крае — '
        f'{st["n"]} '
        f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
        f' | {C.BRAND}'
    )

    seo_desc = (
        f'{tm["plural"]} в Ставропольском крае: '
        f'{st["n"]} '
        f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
        + (
            f', цены от {fmt_price_plain(st["min"])}'
            if st["min"]
            else ""
        )
        + '. Кисловодск, Пятигорск, Ессентуки, КМВ и Ставрополь. '
        'Подбор, проверка, ипотека и сопровождение сделки.'
    )

    paras = [
        (
            f'Предложения по запросу «купить {tm["gen"]} '
            'в Ставропольском крае». '
            f'В каталоге {st["n"]} '
            f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
            + (
                f', цены от {fmt_price_plain(st["min"])} '
                f'до {fmt_price_plain(st["max"])}'
                if st["min"]
                else ""
            )
            + '. Подбираем объект под бюджет, город и цель покупки.'
        ),
    ]

    return (
        h1,
        seo_title,
        seo_desc,
        paras,
        None,
    )


def empty_texts_type(t):
    tm = type_meta(t)

    return (
        f'{tm["plural"]} — '
        '<em>Ставропольский край</em>',
        f'{tm["plural"]} '
        f'в Ставропольском крае | {C.BRAND}',
        f'{tm["plural"]} в Ставропольском крае. '
        'Оставьте заявку — подберём объект под ваш запрос.',
        [],
        None,
    )


def empty_texts_city(c):
    cp = city_prep(c)

    return (
        f'Недвижимость {cp}',
        f'Недвижимость {cp} | {C.BRAND}',
        f'Недвижимость {cp}, Ставропольский край: '
        'подбор квартир, домов и участков. '
        'Оставьте заявку — подберём объект.',
        [],
        None,
    )


def empty_texts_region(r):
    rp = region_prep(r)

    return (
        f'Недвижимость {rp}',
        f'Недвижимость {rp} | {C.BRAND}',
        f'Недвижимость {rp}. '
        'Оставьте заявку — подберём объект.',
        [],
        None,
    )


# ─────────────────────────── основной проход ───────────────────────────

def build():
    global _hub_seo_links_cache

    if SAMPLE:
        raw = json.load(
            open(
                "sample_listings.json",
                encoding="utf-8"
            )
        )
        settings = json.load(
            open(
                "sample_settings.json",
                encoding="utf-8"
            )
        )
        print(
            "• режим SAMPLE: "
            "данные из sample_listings.json"
        )
    else:
        print(
            f"• тяну объекты "
            f"из {C.PB_URL} …"
        )
        raw = fetch_listings()
        settings = fetch_settings()

    all_objs = [
        normalize(r)
        for r in raw
    ]

    # КЛЮЧЕВО:
    # SEO-каталог строим только по Ставропольскому краю.
    objs = [
        o
        for o in all_objs
        if str(
            o.get("region")
            or ""
        ).strip().casefold()
        == str(
            C.SEO_REGION
        ).strip().casefold()
    ]

    skipped = (
        len(all_objs)
        - len(objs)
    )

    for o in objs:
        o["url"] = obj_url(o)

    print(
        f"• объектов опубликовано всего: "
        f"{len(all_objs)}"
    )
    print(
        f"• объектов для SEO "
        f"«{C.SEO_REGION}»: "
        f"{len(objs)}"
    )

    if skipped:
        print(
            f"• исключено объектов "
            f"из других регионов: "
            f"{skipped}"
        )

    by_type = {}
    by_city = {}
    by_region = {}
    by_city_type = {}

    for o in objs:
        if o.get("type"):
            by_type.setdefault(
                o["type"],
                []
            ).append(o)

        if o.get("city"):
            by_city.setdefault(
                o["city"],
                []
            ).append(o)

        if o.get("region"):
            by_region.setdefault(
                o["region"],
                []
            ).append(o)

        if (
            o.get("city")
            and o.get("type")
        ):
            by_city_type.setdefault(
                (
                    o["city"],
                    o["type"]
                ),
                []
            ).append(o)

    # Приоритетные направления существуют всегда.
    for t in C.PRIORITY_TYPES:
        by_type.setdefault(
            t,
            []
        )

    for c in C.PRIORITY_CITIES:
        by_city.setdefault(
            c,
            []
        )

    for region in C.PRIORITY_REGIONS:
        by_region.setdefault(
            region,
            []
        )

    available_links = (
        [
            (
                type_meta(t)["plural"],
                C.SITE_BASE
                + f'/{type_meta(t)["slug"]}/'
            )
            for t, v
            in by_type.items()
            if v
        ][:6]
        + [
            (
                c,
                C.SITE_BASE
                + f'/gorod/{slugify(c)}/'
            )
            for c, v
            in by_city.items()
            if v
        ][:8]
    )

    _hub_seo_links_cache = (
        [
            (
                type_meta(t)["plural"],
                C.SITE_BASE
                + f'/{type_meta(t)["slug"]}/'
            )
            for t, v
            in sorted(
                by_type.items(),
                key=lambda kv: -len(kv[1])
            )
            if v
        ][:6]
        + [
            (
                c,
                C.SITE_BASE
                + f'/gorod/{slugify(c)}/'
            )
            for c, v
            in sorted(
                by_city.items(),
                key=lambda kv: -len(kv[1])
            )
            if v
        ][:8]
    )

    if os.path.isdir(
        C.OUT_DIR
    ):
        shutil.rmtree(
            C.OUT_DIR
        )

    os.makedirs(
        C.OUT_DIR,
        exist_ok=True
    )

    urls = []

    # ── Корень каталога ──
    # Генерируем, но НЕ добавляем в sitemap.
    write_page(
        "/",
        render_hub(
            objs,
            by_type,
            by_city,
            by_region,
            settings
        ),
        urls,
        index=False,
    )

    # ── Объекты ──
    for o in objs:
        similar = [
            s
            for s in objs
            if s["id"] != o["id"]
            and (
                s.get("city")
                == o.get("city")
                or s.get("type")
                == o.get("type")
            )
        ]

        write_page(
            o["url"],
            render_object(
                o,
                settings,
                similar
            ),
            urls,
            lastmod=(
                str(o.get("updatedAt"))[:10]
                if o.get("updatedAt")
                else None
            ),
        )

    # ── Тип недвижимости ──
    for t, v in by_type.items():
        tm = type_meta(t)
        empty = not v

        (
            h1,
            st_t,
            sd,
            paras,
            faq
        ) = (
            empty_texts_type(t)
            if empty
            else cluster_texts_type(
                t,
                v
            )
        )

        crumbs = [
            (
                "Каталог",
                C.SITE_BASE + "/"
            ),
            (
                tm["plural"],
                None
            )
        ]

        related = (
            available_links
            if empty
            else [
                (
                    c,
                    C.SITE_BASE
                    + f'/gorod/{slugify(c)}/{tm["slug"]}/'
                )
                for (cc, tt), vv
                in by_city_type.items()
                if tt == t
                for c in [cc]
            ][:12]
        )

        write_page(
            f'/{tm["slug"]}/',
            render_cluster(
                kind="type",
                key=t,
                objs=v,
                settings=settings,
                h1=h1,
                seo_title=st_t,
                seo_desc=sd,
                intro_paras=paras,
                crumbs=crumbs,
                related=related,
                faq=faq,
                path=f'/{tm["slug"]}/',
                robots=(
                    "noindex, follow"
                    if empty
                    else (
                        "index, follow, "
                        "max-image-preview:large"
                    )
                ),
            ),
            urls,
            index=not empty,
        )

    # ── Город ──
    for c, v in by_city.items():
        empty = not v

        (
            h1,
            st_t,
            sd,
            paras,
            faq
        ) = (
            empty_texts_city(c)
            if empty
            else cluster_texts_city(
                c,
                v
            )
        )

        crumbs = [
            (
                "Каталог",
                C.SITE_BASE + "/"
            ),
            (
                c,
                None
            )
        ]

        related = (
            available_links
            if empty
            else [
                (
                    type_meta(tt)["plural"],
                    C.SITE_BASE
                    + f'/gorod/{slugify(c)}/{type_meta(tt)["slug"]}/'
                )
                for (cc, tt)
                in by_city_type
                if cc == c
            ]
        )

        write_page(
            f'/gorod/{slugify(c)}/',
            render_cluster(
                kind="city",
                key=c,
                objs=v,
                settings=settings,
                h1=h1,
                seo_title=st_t,
                seo_desc=sd,
                intro_paras=paras,
                crumbs=crumbs,
                related=related,
                faq=faq,
                path=f'/gorod/{slugify(c)}/',
                robots=(
                    "noindex, follow"
                    if empty
                    else (
                        "index, follow, "
                        "max-image-preview:large"
                    )
                ),
            ),
            urls,
            index=not empty,
        )

    # ── Регион ──
    for region, v in by_region.items():
        empty = not v

        (
            h1,
            st_t,
            sd,
            paras,
            faq
        ) = (
            empty_texts_region(region)
            if empty
            else cluster_texts_region(
                region,
                v
            )
        )

        crumbs = [
            (
                "Каталог",
                C.SITE_BASE + "/"
            ),
            (
                region,
                None
            )
        ]

        cities_in = sorted(
            {
                o["city"]
                for o in v
                if o.get("city")
            }
        )

        related = (
            available_links
            if empty
            else [
                (
                    city,
                    C.SITE_BASE
                    + f'/gorod/{slugify(city)}/'
                )
                for city in cities_in
            ][:12]
        )

        write_page(
            f'/region/{slugify(region)}/',
            render_cluster(
                kind="region",
                key=region,
                objs=v,
                settings=settings,
                h1=h1,
                seo_title=st_t,
                seo_desc=sd,
                intro_paras=paras,
                crumbs=crumbs,
                related=related,
                faq=faq,
                path=(
                    f'/region/'
                    f'{slugify(region)}/'
                ),
                robots=(
                    "noindex, follow"
                    if empty
                    else (
                        "index, follow, "
                        "max-image-preview:large"
                    )
                ),
            ),
            urls,
            index=not empty,
        )

    # ── Город × тип ──
    for (c, t), v in by_city_type.items():
        tm = type_meta(t)

        (
            h1,
            st_t,
            sd,
            paras,
            faq
        ) = cluster_texts_city_type(
            c,
            t,
            v
        )

        crumbs = [
            (
                "Каталог",
                C.SITE_BASE + "/"
            ),
            (
                c,
                C.SITE_BASE
                + f'/gorod/{slugify(c)}/'
            ),
            (
                tm["plural"],
                None
            ),
        ]

        related = (
            [
                (
                    type_meta(tt)["plural"],
                    C.SITE_BASE
                    + f'/gorod/{slugify(c)}/{type_meta(tt)["slug"]}/'
                )
                for (cc, tt)
                in by_city_type
                if cc == c
                and tt != t
            ]
            + [
                (
                    city,
                    C.SITE_BASE
                    + f'/gorod/{slugify(city)}/{tm["slug"]}/'
                )
                for (city, tt)
                in by_city_type
                if tt == t
                and city != c
            ]
        )[:12]

        write_page(
            f'/gorod/{slugify(c)}/{tm["slug"]}/',
            render_cluster(
                kind="city_type",
                key=(c, t),
                objs=v,
                settings=settings,
                h1=h1,
                seo_title=st_t,
                seo_desc=sd,
                intro_paras=paras,
                crumbs=crumbs,
                related=related,
                faq=faq,
                path=(
                    f'/gorod/{slugify(c)}/'
                    f'{tm["slug"]}/'
                ),
            ),
            urls,
        )

    write_sitemap(urls)
    write_robots()
    write_cname()

    print(
        f"• индексируемых URL "
        f"в sitemap: {len(urls)}"
    )
    print(
        f"  — объектов: {len(objs)}"
    )
    print(
        f"  — типы: {len(by_type)}"
        f" | города: {len(by_city)}"
        f" | регионы: {len(by_region)}"
        f" | город×тип: {len(by_city_type)}"
    )
    print(
        "• корень catalog.horizontriel.com/: "
        "noindex, follow; canonical -> "
        f"{C.MAIN_SITE}/"
    )
    print(
        f"• готово -> {C.OUT_DIR}/ "
        "(sitemap.xml, robots.txt, CNAME)"
    )


if __name__ == "__main__":
    build()
