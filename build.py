#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор статических SEO-страниц HorizonTriel.
Тянет опубликованные объекты из PocketBase и собирает:
  • страницу каждого объекта  /obekt/{slug}/
  • кластерные посадочные     /{type}/  /gorod/{city}/  /region/{region}/  /gorod/{city}/{type}/
  • хаб-каталог               /
  • sitemap.xml + robots.txt
Запуск локально на тестовых данных:  python build.py --sample
Боевой запуск (в CI):               python build.py
"""
import os, sys, json, shutil, urllib.request, urllib.error
from datetime import date
from urllib.parse import urlparse, quote

import config as C
from config import (slugify, type_meta, city_prep, region_prep, plural_ru,
                    fmt_price_plain, fmt_num)
import templates as T
from templates import esc, esc_attr, page, card, breadcrumbs_html, footer, json_ld

SAMPLE = "--sample" in sys.argv or os.environ.get("SAMPLE") == "1"


# ─────────────────────────── загрузка данных ───────────────────────────
def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "horizontriel-seo/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_listings():
    fields = ("id,title,type,tag,region,city,address,description,residential_complex,"
              "completion_date,promotion,price,area,living_area,kitchen_area,year,floor,"
              "floors,rooms,land,land_purpose,plot_frontage,wall_material,communications,"
              "condition,deal,published,featured,sort_order,features,images,floorplans,created,updated")
    url = (f"{C.PB_URL}/api/collections/{C.PB_COLLECTION}/records"
           f"?filter=(published=true)&sort=sort_order,created&perPage=500&fields={quote(fields)}")
    data = _get_json(url)
    return data.get("items") or data.get("records") or []


def fetch_settings():
    try:
        d = _get_json(f"{C.PB_URL}/api/collections/{C.PB_SETTINGS}/records?perPage=1&sort=created")
        items = d.get("items") or []
        rec = items[0] if items else {}
    except Exception:
        rec = {}
    return {
        "tel":   rec.get("tel")   or C.FALLBACK_SETTINGS["tel"],
        "wa":    rec.get("wa")    or C.FALLBACK_SETTINGS["wa"],
        "tg":    rec.get("tg")    or C.FALLBACK_SETTINGS["tg"],
        "max":   rec.get("max_url") or rec.get("max") or C.FALLBACK_SETTINGS["max"],
        "email": rec.get("email") or C.FALLBACK_SETTINGS["email"],
    }


# ─────────────────────────── нормализация (как pbToListing) ───────────────────────────
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
            out.append(f"{C.PB_URL}/api/files/{C.PB_COLLECTION}/{rec_id}/{name}")
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
    feats = feats_raw if isinstance(feats_raw, list) else ([feats_raw] if feats_raw else [])
    return {
        "id": r.get("id"), "title": r.get("title"), "type": r.get("type"), "tag": r.get("tag"),
        "region": r.get("region"), "city": r.get("city"), "address": r.get("address"),
        "desc": r.get("description"),
        "residential_complex": r.get("residential_complex"),
        "completion_date": r.get("completion_date"), "promotion": r.get("promotion"),
        "price": int(r.get("price") or 0),
        "area": r.get("area"), "living_area": r.get("living_area"), "kitchen_area": r.get("kitchen_area"),
        "year": r.get("year"), "floor": r.get("floor"), "floors": r.get("floors"), "rooms": r.get("rooms"),
        "land": r.get("land"), "land_purpose": r.get("land_purpose"), "plot_frontage": r.get("plot_frontage"),
        "wall_material": r.get("wall_material"), "communications": r.get("communications"),
        "condition": r.get("condition"), "deal": r.get("deal"),
        "featured": r.get("featured"), "order": r.get("sort_order"),
        "features": [_norm_feature(f) for f in feats if f],
        "images": _files_to_urls(r.get("id"), r.get("images")),
        "floorplans": _files_to_urls(r.get("id"), r.get("floorplans") or r.get("floorplan") or r.get("plans")),
        "createdAt": r.get("created"), "updatedAt": r.get("updated"),
    }


def obj_url(o):
    base = slugify(o.get("title") or o.get("type") or "obekt") or "obekt"
    sid = (o.get("id") or "")[-6:]
    return f"/obekt/{base}-{sid}/"


# ─────────────────────────── помощники контента ───────────────────────────
def price_stats(objs):
    prices = [o["price"] for o in objs if o.get("price")]
    areas = [float(o["area"]) for o in objs if o.get("area") and str(o["area"]).replace(".", "").isdigit()]
    return {
        "n": len(objs),
        "min": min(prices) if prices else 0,
        "max": max(prices) if prices else 0,
        "avg_area": round(sum(areas) / len(areas)) if areas else 0,
    }


def facts_row(st, genpl):
    cells = []
    word = plural_ru(st["n"], "объект", "объекта", "объектов")
    cells.append(('<div class="fact"><div class="n">%d</div><div class="l">%s в подборке</div></div>'
                  % (st["n"], word)))
    if st["min"]:
        cells.append('<div class="fact"><div class="n">%s</div><div class="l">Цена от</div></div>'
                     % fmt_price_plain(st["min"]).replace(" ₽", "").strip() + " ₽")
    if st["avg_area"]:
        cells.append('<div class="fact"><div class="n">%s м²</div><div class="l">Средняя площадь</div></div>'
                     % st["avg_area"])
    return '<div class="facts">' + "".join(cells) + "</div>"


def faq_html(qas):
    items = "".join(
        f'<details><summary>{esc(q)}</summary><div class="a">{a}</div></details>' for q, a in qas
    )
    return ('<div class="wrap section"><div class="eyebrow">Частые вопросы</div>'
            f'<div class="faq">{items}</div></div>')


def related_pills(links):
    if not links:
        return ""
    pills = "".join(f'<a class="pill" href="{esc_attr(u)}">{esc(l)}</a>' for l, u in links)
    return f'<div class="wrap"><div class="pills">{pills}</div></div>'


# ─────────────────────────── страница объекта ───────────────────────────
def render_object(o, settings, similar):
    url_abs = C.SITE_BASE + o["url"]
    tmeta = type_meta(o.get("type"))
    place = " · ".join([x for x in (o.get("region"), o.get("city")) if x])

    title_bits = [o.get("title") or "Объект недвижимости"]
    loc = ", ".join([x for x in (o.get("city"), o.get("region")) if x])
    if loc: title_bits.append(loc)
    if o.get("area"): title_bits.append(f'{o["area"]} м²')
    if o.get("price"): title_bits.append(fmt_price_plain(o["price"]))
    seo_title = " — ".join(title_bits) + f" | {C.BRAND}"

    d_bits = [f'{o.get("deal") or "Продажа"}: {o.get("title") or "объект недвижимости"}']
    dl = ", ".join([x for x in (o.get("region"), o.get("city"), o.get("address")) if x])
    if dl: d_bits.append(dl)
    if o.get("area"): d_bits.append(f'{o["area"]} м²')
    if o.get("rooms"): d_bits.append(f'{o["rooms"]} комн.')
    if o.get("price"): d_bits.append(fmt_price_plain(o["price"]))
    seo_desc = ". ".join(d_bits)[:240]

    # галерея
    imgs = o.get("images") or []
    plans = o.get("floorplans") or []
    gal = '<div class="gallery">'
    if imgs:
        gal += f'<div class="gal-main"><img src="{esc_attr(imgs[0])}" alt="{esc_attr(o.get("title"))}"></div>'
        if len(imgs) > 1:
            gal += '<div class="gal-thumbs">' + "".join(
                f'<img src="{esc_attr(u)}" alt="{esc_attr(o.get("title"))} — фото {i+2}" loading="lazy">'
                for i, u in enumerate(imgs[1:9])) + "</div>"
    if plans:
        gal += '<div class="plans-lbl">Планировка</div>'
        gal += '<div class="gal-thumbs">' + "".join(
            f'<img src="{esc_attr(u)}" alt="{esc_attr(o.get("title"))} — планировка {i+1}" loading="lazy">'
            for i, u in enumerate(plans[:6])) + "</div>"
    if not imgs and not plans:
        gal += '<div class="gal-main card-noimg"><span>Фото готовится</span></div>'
    gal += "</div>"

    # параметры (как в модалке)
    P = []
    def add(lbl, val):
        if val not in (None, "", 0):
            P.append((lbl, val))
    add("Регион", o.get("region"))
    add("ЖК", o.get("residential_complex"))
    add("Срок сдачи", o.get("completion_date"))
    add("Общая площадь", f'{o["area"]} м²' if o.get("area") else None)
    add("Жилая площадь", f'{o["living_area"]} м²' if o.get("living_area") else None)
    add("Площадь кухни", f'{o["kitchen_area"]} м²' if o.get("kitchen_area") else None)
    add("Комнат", o.get("rooms"))
    if o.get("floor") and o.get("floors"):
        add("Этаж", f'{o["floor"]} из {o["floors"]}')
    elif o.get("floor"):
        add("Этаж", o.get("floor"))
    add("Год", o.get("year"))
    add("Участок", f'{o["land"]} сот.' if o.get("land") else None)
    add("Назначение земли", o.get("land_purpose"))
    add("Фасад участка", f'{o["plot_frontage"]} м' if o.get("plot_frontage") else None)
    add("Материал стен", o.get("wall_material"))
    add("Коммуникации", o.get("communications"))
    add("Состояние", o.get("condition"))
    add("Тип", o.get("type"))
    add("Адрес", o.get("address"))
    params = '<div class="params">' + "".join(
        f'<div class="p"><div class="plbl">{esc(l)}</div><div class="pval">{esc(v)}</div></div>' for l, v in P
    ) + "</div>"

    promo = ""
    if o.get("promotion"):
        promo = f'<div class="promo"><b>Акция / спецпредложение</b>{esc(o["promotion"])}</div>'
    desc = f'<div class="desc">{esc(o["desc"])}</div>' if o.get("desc") else ""
    feats = ""
    if o.get("features"):
        chips = "".join(f'<span class="feat">{esc(f)}</span>' for f in o["features"])
        feats = f'<div class="feats-lbl">Особенности</div><div class="feats">{chips}</div>'

    # CTA
    wa_msg = quote(f'Здравствуйте! Интересует: {o.get("title") or ""}'
                   + (f' ({place})' if place else "") + f' — {fmt_price_plain(o.get("price"))}\n{url_abs}')
    tel_href = "".join(c for c in settings["tel"] if c.isdigit() or c == "+")
    cta = ('<div class="cta">'
           f'<a class="btn btn-wa" href="https://wa.me/{esc_attr(settings["wa"])}?text={wa_msg}" target="_blank" rel="noopener">WhatsApp</a>'
           f'<a class="btn btn-tg" href="{esc_attr(settings["tg"])}" target="_blank" rel="noopener">Telegram</a>'
           + (f'<a class="btn btn-max" href="{esc_attr(settings["max"])}" target="_blank" rel="noopener">MAX</a>' if settings.get("max") else "")
           + f'<a class="btn btn-call" href="tel:{esc_attr(tel_href)}">Позвонить</a>'
           '</div>')

    price_row = (f'<div class="price-row"><div class="price-big">{esc(fmt_price_plain(o.get("price")))}</div>'
                 + (f'<span class="deal">{esc(o.get("deal"))}</span>' if o.get("deal") else "") + "</div>")

    # хлебные крошки
    crumbs = [("Каталог", C.SITE_BASE + "/")]
    if o.get("city"):
        crumbs.append((o["city"], C.SITE_BASE + f'/gorod/{slugify(o["city"])}/'))
    if o.get("type"):
        crumbs.append((tmeta["plural"], C.SITE_BASE + f'/{tmeta["slug"]}/'))
    crumbs.append((o.get("title") or "Объект", None))

    similar_html = ""
    if similar:
        similar_html = ('<div class="wrap section"><h2>Похожие объекты</h2>'
                        '<div class="grid">' + "".join(card(s) for s in similar[:4]) + "</div></div>")

    body = (
        breadcrumbs_html(crumbs)
        + '<div class="wrap section"><div class="obj">'
        + gal
        + '<div class="obj-side">'
        + (f'<div class="place">{esc(place)}</div>' if place else "")
        + f'<h1>{esc(o.get("title") or "Объект недвижимости")}</h1>'
        + price_row + params + promo + desc + feats + cta
        + '</div></div></div>'
        + similar_html
        + footer(settings, _hub_seo_links_cache)
    )

    # schema
    ld_listing = {
        "@context": "https://schema.org", "@type": "RealEstateListing",
        "name": o.get("title") or "Объект недвижимости",
        "description": o.get("desc") or seo_desc,
        "url": url_abs,
        "datePosted": (str(o.get("createdAt"))[:10] if o.get("createdAt") else None),
        "image": (o.get("images") or [])[:12],
        "address": {"@type": "PostalAddress", "addressCountry": "RU",
                    "addressRegion": o.get("region") or "", "addressLocality": o.get("city") or "",
                    "streetAddress": o.get("address") or ""},
        "offers": {"@type": "Offer", "priceCurrency": "RUB",
                   "price": o.get("price") or None,
                   "availability": "https://schema.org/InStock", "url": url_abs},
    }
    ld_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList",
             "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n,
                                  "item": (u or url_abs)} for i, (n, u) in enumerate(crumbs)]}
    og_img = (o.get("images") or [None])[0]
    return page(title=seo_title, description=seo_desc, canonical=url_abs,
                body=body, jsonld=[ld_listing, ld_bc], og_image=og_img)


# ─────────────────────────── кластерная посадочная ───────────────────────────
_hub_seo_links_cache = []  # заполняется в build(), нужен футеру

def contact_cta(settings):
    tel_href = "".join(c for c in settings["tel"] if c.isdigit() or c == "+")
    return ('<div class="cta">'
            f'<a class="btn btn-wa" href="https://wa.me/{esc_attr(settings["wa"])}" target="_blank" rel="noopener">WhatsApp</a>'
            f'<a class="btn btn-tg" href="{esc_attr(settings["tg"])}" target="_blank" rel="noopener">Telegram</a>'
            + (f'<a class="btn btn-max" href="{esc_attr(settings["max"])}" target="_blank" rel="noopener">MAX</a>' if settings.get("max") else "")
            + f'<a class="btn btn-call" href="tel:{esc_attr(tel_href)}">Позвонить</a>'
            '</div>')


def render_cluster(*, kind, key, objs, settings, h1, seo_title, seo_desc, intro_paras,
                   crumbs, related, faq, path, robots="index, follow, max-image-preview:large"):
    url_abs = C.SITE_BASE + path

    # ── пустая категория: 200 + noindex, без сетки/FAQ ──
    if not objs:
        body = (
            breadcrumbs_html(crumbs)
            + '<div class="wrap section">'
            + f'<div class="eyebrow">Каталог · {esc(kind_label(kind))}</div>'
            + f'<h1>{h1}</h1>'
            + '<div class="prose"><p>В этой категории пока нет опубликованных объектов. '
              'Оставьте заявку — подберём подходящий вариант под ваш бюджет и цель и пришлём подборку.</p></div>'
            + contact_cta(settings)
            + related_pills(related)
            + footer(settings, _hub_seo_links_cache)
        )
        ld = [
            {"@context": "https://schema.org", "@type": "CollectionPage",
             "name": strip_tags(h1), "url": url_abs, "inLanguage": "ru-RU"},
            {"@context": "https://schema.org", "@type": "BreadcrumbList",
             "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n,
                                  "item": (u or url_abs)} for i, (n, u) in enumerate(crumbs)]},
        ]
        return page(title=seo_title, description=seo_desc, canonical=url_abs,
                    body=body, jsonld=ld, robots=robots)

    st = price_stats(objs)

    grid = '<div class="grid">' + "".join(card(o) for o in objs) + "</div>"
    prose = ""
    if intro_paras:
        prose = '<div class="prose">' + "".join(f"<p>{esc(p)}</p>" for p in intro_paras) + "</div>"

    body = (
        breadcrumbs_html(crumbs)
        + '<div class="wrap section">'
        + f'<div class="eyebrow">Каталог · {esc(kind_label(kind))}</div>'
        + f'<h1>{h1}</h1>'
        + facts_row(st, "")
        + prose
        + grid
        + "</div>"
        + related_pills(related)
        + (faq_html(faq) if faq else "")
        + footer(settings, _hub_seo_links_cache)
    )

    ld_items = {"@context": "https://schema.org", "@type": "ItemList",
                "name": strip_tags(h1),
                "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                     "url": C.SITE_BASE + o["url"],
                                     "name": o.get("title") or "Объект недвижимости"}
                                    for i, o in enumerate(objs[:50])]}
    ld_page = {"@context": "https://schema.org", "@type": "CollectionPage",
               "name": strip_tags(h1), "url": url_abs, "inLanguage": "ru-RU"}
    ld_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList",
             "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n,
                                  "item": (u or url_abs)} for i, (n, u) in enumerate(crumbs)]}
    ld = [ld_page, ld_items, ld_bc]
    if faq:
        ld.append({"@context": "https://schema.org", "@type": "FAQPage",
                   "mainEntity": [{"@type": "Question", "name": strip_tags(q),
                                   "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}}
                                  for q, a in faq]})
    og_img = next((o["images"][0] for o in objs if o.get("images")), None)
    return page(title=seo_title, description=seo_desc, canonical=url_abs,
                body=body, jsonld=ld, og_image=og_img, robots=robots)


def kind_label(kind):
    return {"type": "По типу", "city": "По городу", "region": "По региону",
            "city_type": "Город и тип"}.get(kind, "Каталог")


def strip_tags(s):
    import re
    return re.sub(r"<[^>]+>", "", str(s)).strip()


# ─────────────────────────── хаб ───────────────────────────
def render_hub(objs, by_type, by_city, by_region, settings):
    url_abs = C.SITE_BASE + "/"
    seo_title = f"Недвижимость по России — квартиры, дома, участки, гаражи и коммерческие объекты | {C.BRAND}"
    seo_desc = (f"{C.BRAND} — каталог недвижимости по России. Квартиры, апартаменты, дома, таунхаусы, "
                "дуплексы, земельные участки, гаражи и коммерческие объекты. Подбор, проверка, ипотека "
                "и сопровождение сделки.")
    st = price_stats(objs)

    def link_list(pairs):
        return '<div class="pills">' + "".join(
            f'<a class="pill" href="{esc_attr(u)}">{esc(l)} · {n}</a>' for l, u, n in pairs) + "</div>"

    type_links = [(type_meta(t)["plural"], C.SITE_BASE + f'/{type_meta(t)["slug"]}/', len(v))
                  for t, v in sorted(by_type.items(), key=lambda kv: -len(kv[1])) if v]
    city_links = [(c, C.SITE_BASE + f'/gorod/{slugify(c)}/', len(v))
                  for c, v in sorted(by_city.items(), key=lambda kv: -len(kv[1])) if v]
    region_links = [(rg, C.SITE_BASE + f'/region/{slugify(rg)}/', len(v))
                    for rg, v in sorted(by_region.items(), key=lambda kv: -len(kv[1])) if v]

    featured = [o for o in objs if o.get("featured")][:8] or objs[:8]
    feat_grid = '<div class="grid">' + "".join(card(o) for o in featured) + "</div>"

    intro = (
        '<div class="prose">'
        f'<p>{C.BRAND} помогает купить и продать недвижимость по всей России: квартиры, апартаменты, '
        'дома, коттеджи, таунхаусы, дуплексы, земельные участки, гаражи, офисы и коммерческие объекты. '
        'Мы подбираем варианты для жизни, переезда, отдыха, аренды, бизнеса и инвестиций.</p>'
        f'<p>Сейчас в каталоге {st["n"]} '
        f'{plural_ru(st["n"], "объект", "объекта", "объектов")}'
        + (f', цены от {fmt_price_plain(st["min"])}' if st["min"] else "")
        + '. Для каждого объекта — проверка юридической чистоты, оценка ликвидности, помощь с ипотекой '
        'и сопровождение сделки до передачи ключей.</p></div>'
    )

    body = (
        '<div class="wrap section">'
        '<div class="eyebrow">Федеральный каталог недвижимости</div>'
        '<h1>Недвижимость <em>по России</em></h1>'
        + facts_row(st, "объектов")
        + intro
        + '</div>'
        + '<div class="wrap section"><h2>По типу недвижимости</h2>' + link_list(type_links) + '</div>'
        + ('<div class="wrap section"><h2>По городам</h2>' + link_list(city_links) + '</div>' if city_links else "")
        + ('<div class="wrap section"><h2>По регионам</h2>' + link_list(region_links) + '</div>' if region_links else "")
        + '<div class="wrap section"><h2>Избранные объекты</h2>' + feat_grid + '</div>'
        + footer(settings, _hub_seo_links_cache)
    )
    ld = [
        {"@context": "https://schema.org", "@type": "WebSite", "name": C.BRAND,
         "url": url_abs, "inLanguage": "ru-RU"},
        {"@context": "https://schema.org", "@type": "RealEstateAgent", "name": C.BRAND,
         "url": url_abs, "email": settings["email"], "telephone": settings["tel"],
         "areaServed": {"@type": "Country", "name": "Россия"},
         "sameAs": [x for x in (settings.get("tg"), settings.get("max")) if x]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList",
         "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Недвижимость по России",
                              "item": url_abs}]},
    ]
    og_img = next((o["images"][0] for o in objs if o.get("images")), None)
    return page(title=seo_title, description=seo_desc, canonical=url_abs,
                body=body, jsonld=ld, og_image=og_img)


# ─────────────────────────── запись файлов + sitemap ───────────────────────────
def write_page(path, html_str, urls, lastmod=None, index=True):
    """path — вида '/gorod/sochi/'. Пишем index.html внутри. index=False → не в sitemap."""
    rel = path.strip("/")
    out = os.path.join(C.OUT_DIR, rel) if rel else C.OUT_DIR
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_str)
    if index:
        urls.append((C.SITE_BASE + path, lastmod or date.today().isoformat()))


def write_sitemap(urls):
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lm in urls:
        body.append(f"<url><loc>{esc(loc)}</loc><lastmod>{lm}</lastmod></url>")
    body.append("</urlset>")
    with open(os.path.join(C.OUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(body))


def write_robots():
    txt = f"User-agent: *\nAllow: /\n\nSitemap: {C.SITE_BASE}/sitemap.xml\n"
    with open(os.path.join(C.OUT_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(txt)


def write_cname():
    host = urlparse(C.SITE_BASE).netloc
    if host:
        with open(os.path.join(C.OUT_DIR, "CNAME"), "w", encoding="utf-8") as f:
            f.write(host + "\n")


# ─────────────────────────── тексты кластеров ───────────────────────────
def cluster_texts_city_type(city, ttype, objs):
    tm = type_meta(ttype)
    cp = city_prep(city)
    st = price_stats(objs)
    h1 = f'Купить {tm["gen"]} {cp} — <em>{C.BRAND}</em>'
    seo_title = f'Купить {tm["gen"]} {cp} — {st["n"]} {plural_ru(st["n"], "объект","объекта","объектов")} | {C.BRAND}'
    seo_desc = (f'{tm["plural"]} {cp}: {st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")} в каталоге'
                + (f', цены от {fmt_price_plain(st["min"])}' if st["min"] else "")
                + '. Подбор, проверка объекта, ипотека и сопровождение сделки.')
    paras = [
        f'Актуальные предложения по запросу «{tm["plural"].lower()} {cp}». '
        + f'В подборке {st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")}'
        + (f', цены начинаются от {fmt_price_plain(st["min"])}' if st["min"] else "")
        + (f', средняя площадь около {st["avg_area"]} м²' if st["avg_area"] else "") + '.',
        f'Мы проверяем каждый объект: юридическую чистоту, обременения, реальные расходы и ликвидность. '
        f'Помогаем с ипотекой и сопровождаем сделку {cp} до передачи ключей.',
    ]
    faq = [
        (f'Какие цены на {tm["plural"].lower()} {cp}?',
         (f'В каталоге {st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")}'
          + (f', цены от {fmt_price_plain(st["min"])} до {fmt_price_plain(st["max"])}' if st["min"] else "")
          + '. Точную стоимость подходящего объекта уточним при подборе.')),
        ('Проверяете ли вы объект перед покупкой?',
         'Да. Проверяем документы, историю перехода прав, обременения, а также инфраструктуру района '
         'и ликвидность объекта — чтобы покупка была безопасной.'),
        ('Можно ли оформить ипотеку?',
         'Да, подбираем ипотечные программы банков под конкретный объект и помогаем с оформлением.'),
    ]
    return h1, seo_title, seo_desc, paras, faq


def cluster_texts_city(city, objs):
    cp = city_prep(city)
    st = price_stats(objs)
    h1 = f'Недвижимость {cp} — <em>каталог</em>'
    seo_title = f'Недвижимость {cp} — купить квартиру, дом или участок | {C.BRAND}'
    seo_desc = (f'Каталог недвижимости {cp}: квартиры, дома, участки, гаражи и коммерческие объекты. '
                f'{st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")}'
                + (f', цены от {fmt_price_plain(st["min"])}' if st["min"] else "")
                + '. Подбор, проверка, ипотека и сопровождение сделки.')
    paras = [
        f'Подбор и продажа недвижимости {cp}: квартиры, апартаменты, дома, таунхаусы, земельные участки, '
        f'гаражи и коммерческие помещения. '
        f'В каталоге {st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")}'
        + (f', цены от {fmt_price_plain(st["min"])}' if st["min"] else "") + '.',
        f'Помогаем купить и продать объект {cp}: проверяем документы, оцениваем ликвидность, '
        'подбираем ипотеку и сопровождаем сделку от первого показа до регистрации права.',
    ]
    faq = [
        (f'Какую недвижимость можно купить {cp}?',
         f'В каталоге {cp} есть квартиры, дома, таунхаусы, земельные участки, гаражи и коммерческие '
         'объекты. Подберём вариант под бюджет, район и цель покупки.'),
        ('Помогаете ли с продажей?',
         'Да. Оцениваем объект, готовим к сделке, находим покупателя и сопровождаем оформление.'),
    ]
    return h1, seo_title, seo_desc, paras, faq


def cluster_texts_region(region, objs):
    rp = region_prep(region)
    st = price_stats(objs)
    h1 = f'Недвижимость {rp}'
    seo_title = f'Недвижимость {rp} — квартиры, дома и участки | {C.BRAND}'
    seo_desc = (f'Объекты недвижимости {rp}: {st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")}'
                + (f', цены от {fmt_price_plain(st["min"])}' if st["min"] else "")
                + '. Подбор, проверка и сопровождение сделки.')
    paras = [
        f'Каталог недвижимости {rp}. Квартиры, дома, участки, гаражи и коммерческие объекты в городах региона. '
        f'В подборке {st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")}'
        + (f', цены от {fmt_price_plain(st["min"])}' if st["min"] else "") + '.',
    ]
    return h1, seo_title, seo_desc, paras, None


def cluster_texts_type(ttype, objs):
    tm = type_meta(ttype)
    st = price_stats(objs)
    h1 = f'{tm["plural"]} — <em>купить по России</em>'
    seo_title = f'Купить {tm["gen"]} — {st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")} по России | {C.BRAND}'
    seo_desc = (f'{tm["plural"]} по России: {st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")}'
                + (f', цены от {fmt_price_plain(st["min"])}' if st["min"] else "")
                + '. Подбор, проверка объекта, ипотека и сопровождение сделки.')
    paras = [
        f'Предложения по запросу «купить {tm["gen"]}» по всей России. '
        f'В каталоге {st["n"]} {plural_ru(st["n"],"объект","объекта","объектов")}'
        + (f', цены от {fmt_price_plain(st["min"])} до {fmt_price_plain(st["max"])}' if st["min"] else "")
        + '. Подбираем объект под бюджет, регион и цель покупки.',
    ]
    return h1, seo_title, seo_desc, paras, None


# ── заголовки для пустых (noindex) страниц приоритетных направлений ──
def empty_texts_type(t):
    tm = type_meta(t)
    return (f'{tm["plural"]} — <em>купить по России</em>', f'{tm["plural"]} по России | {C.BRAND}',
            f'{tm["plural"]} по России. Оставьте заявку — подберём объект под ваш запрос.', [], None)

def empty_texts_city(c):
    cp = city_prep(c)
    return (f'Недвижимость {cp}', f'Недвижимость {cp} | {C.BRAND}',
            f'Недвижимость {cp}: подбор квартир, домов и участков. Оставьте заявку — подберём объект.', [], None)

def empty_texts_region(r):
    rp = region_prep(r)
    return (f'Недвижимость {rp}', f'Недвижимость {rp} | {C.BRAND}',
            f'Недвижимость {rp}. Оставьте заявку — подберём объект.', [], None)


# ─────────────────────────── основной проход ───────────────────────────
def build():
    global _hub_seo_links_cache

    if SAMPLE:
        raw = json.load(open("sample_listings.json", encoding="utf-8"))
        settings = json.load(open("sample_settings.json", encoding="utf-8"))
        print("• режим SAMPLE: данные из sample_listings.json")
    else:
        print(f"• тяну объекты из {C.PB_URL} …")
        raw = fetch_listings()
        settings = fetch_settings()
    objs = [normalize(r) for r in raw]
    for o in objs:
        o["url"] = obj_url(o)
    print(f"• объектов опубликовано: {len(objs)}")

    # группировки (только непустые)
    by_type, by_city, by_region, by_city_type = {}, {}, {}, {}
    for o in objs:
        if o.get("type"):
            by_type.setdefault(o["type"], []).append(o)
        if o.get("city"):
            by_city.setdefault(o["city"], []).append(o)
        if o.get("region"):
            by_region.setdefault(o["region"], []).append(o)
        if o.get("city") and o.get("type"):
            by_city_type.setdefault((o["city"], o["type"]), []).append(o)

    # приоритетные направления (ссылки подвала) должны существовать всегда
    for t in C.PRIORITY_TYPES:
        by_type.setdefault(t, [])
    for c in C.PRIORITY_CITIES:
        by_city.setdefault(c, [])
    for rg in C.PRIORITY_REGIONS:
        by_region.setdefault(rg, [])

    # куда вести с пустых страниц — на направления, где объекты есть
    available_links = ([(type_meta(t)["plural"], C.SITE_BASE + f'/{type_meta(t)["slug"]}/')
                        for t, v in by_type.items() if v][:6]
                       + [(c, C.SITE_BASE + f'/gorod/{slugify(c)}/')
                          for c, v in by_city.items() if v][:8])

    # ссылки для футера (топ-направления)
    _hub_seo_links_cache = (
        [(type_meta(t)["plural"], C.SITE_BASE + f'/{type_meta(t)["slug"]}/')
         for t, v in sorted(by_type.items(), key=lambda kv: -len(kv[1])) if v][:6]
        + [(c, C.SITE_BASE + f'/gorod/{slugify(c)}/')
           for c, v in sorted(by_city.items(), key=lambda kv: -len(kv[1])) if v][:8]
    )

    # свежая директория
    if os.path.isdir(C.OUT_DIR):
        shutil.rmtree(C.OUT_DIR)
    os.makedirs(C.OUT_DIR, exist_ok=True)
    urls = []

    # ── хаб ──
    write_page("/", render_hub(objs, by_type, by_city, by_region, settings), urls)

    # ── объекты ──
    for o in objs:
        similar = [s for s in objs if s["id"] != o["id"]
                   and (s.get("city") == o.get("city") or s.get("type") == o.get("type"))]
        write_page(o["url"], render_object(o, settings, similar), urls,
                   lastmod=(str(o.get("updatedAt"))[:10] if o.get("updatedAt") else None))

    # ── тип по России ──
    for t, v in by_type.items():
        tm = type_meta(t)
        empty = not v
        h1, st_t, sd, paras, faq = (empty_texts_type(t) if empty else cluster_texts_type(t, v))
        crumbs = [("Каталог", C.SITE_BASE + "/"), (tm["plural"], None)]
        related = (available_links if empty else
                   [(c, C.SITE_BASE + f'/gorod/{slugify(c)}/{tm["slug"]}/')
                    for (cc, tt), vv in by_city_type.items() if tt == t for c in [cc]][:12])
        write_page(f'/{tm["slug"]}/', render_cluster(
            kind="type", key=t, objs=v, settings=settings, h1=h1, seo_title=st_t, seo_desc=sd,
            intro_paras=paras, crumbs=crumbs, related=related, faq=faq, path=f'/{tm["slug"]}/',
            robots=("noindex, follow" if empty else "index, follow, max-image-preview:large")),
            urls, index=not empty)

    # ── город ──
    for c, v in by_city.items():
        empty = not v
        h1, st_t, sd, paras, faq = (empty_texts_city(c) if empty else cluster_texts_city(c, v))
        crumbs = [("Каталог", C.SITE_BASE + "/"), (c, None)]
        related = (available_links if empty else
                   [(type_meta(tt)["plural"], C.SITE_BASE + f'/gorod/{slugify(c)}/{type_meta(tt)["slug"]}/')
                    for (cc, tt) in by_city_type if cc == c])
        write_page(f'/gorod/{slugify(c)}/', render_cluster(
            kind="city", key=c, objs=v, settings=settings, h1=h1, seo_title=st_t, seo_desc=sd,
            intro_paras=paras, crumbs=crumbs, related=related, faq=faq, path=f'/gorod/{slugify(c)}/',
            robots=("noindex, follow" if empty else "index, follow, max-image-preview:large")),
            urls, index=not empty)

    # ── регион ──
    for rg, v in by_region.items():
        empty = not v
        h1, st_t, sd, paras, faq = (empty_texts_region(rg) if empty else cluster_texts_region(rg, v))
        crumbs = [("Каталог", C.SITE_BASE + "/"), (rg, None)]
        cities_in = sorted({o["city"] for o in v if o.get("city")})
        related = (available_links if empty else
                   [(ci, C.SITE_BASE + f'/gorod/{slugify(ci)}/') for ci in cities_in][:12])
        write_page(f'/region/{slugify(rg)}/', render_cluster(
            kind="region", key=rg, objs=v, settings=settings, h1=h1, seo_title=st_t, seo_desc=sd,
            intro_paras=paras, crumbs=crumbs, related=related, faq=faq, path=f'/region/{slugify(rg)}/',
            robots=("noindex, follow" if empty else "index, follow, max-image-preview:large")),
            urls, index=not empty)

    # ── город × тип ──
    for (c, t), v in by_city_type.items():
        tm = type_meta(t)
        h1, st_t, sd, paras, faq = cluster_texts_city_type(c, t, v)
        crumbs = [("Каталог", C.SITE_BASE + "/"),
                  (c, C.SITE_BASE + f'/gorod/{slugify(c)}/'), (tm["plural"], None)]
        # соседи: другие типы в этом городе + этот тип в других городах
        related = ([(type_meta(tt)["plural"], C.SITE_BASE + f'/gorod/{slugify(c)}/{type_meta(tt)["slug"]}/')
                    for (cc, tt) in by_city_type if cc == c and tt != t]
                   + [(ci, C.SITE_BASE + f'/gorod/{slugify(ci)}/{tm["slug"]}/')
                      for (ci, tt) in by_city_type if tt == t and ci != c])[:12]
        write_page(f'/gorod/{slugify(c)}/{tm["slug"]}/', render_cluster(
            kind="city_type", key=(c, t), objs=v, settings=settings, h1=h1, seo_title=st_t, seo_desc=sd,
            intro_paras=paras, crumbs=crumbs, related=related, faq=faq,
            path=f'/gorod/{slugify(c)}/{tm["slug"]}/'), urls)

    write_sitemap(urls)
    write_robots()
    write_cname()

    print(f"• страниц собрано: {len(urls)}")
    print(f"  — объектов: {len(objs)}")
    print(f"  — типы: {len(by_type)} | города: {len(by_city)} | регионы: {len(by_region)} | город×тип: {len(by_city_type)}")
    print(f"• готово → {C.OUT_DIR}/ (sitemap.xml, robots.txt, CNAME)")


if __name__ == "__main__":
    build()
