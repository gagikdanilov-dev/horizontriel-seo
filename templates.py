# -*- coding: utf-8 -*-
"""HTML-шаблоны генератора. Визуально повторяют главный сайт HorizonTriel."""
import html as _html
import json
from config import BRAND, SITE_BASE, MAIN_SITE

def esc(s):
    return _html.escape("" if s is None else str(s), quote=True)

def esc_attr(s):
    return _html.escape("" if s is None else str(s), quote=True)

# ─────────────────────────── общий CSS (токены сайта) ───────────────────────────
CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --cream:#F5F1EB;--cream-dark:#EDE8DF;--stone:#C8BFB0;--stone-dark:#8A8178;
  --ink:#1A1814;--ink-mid:#3D3930;--ink-light:#6B6560;
  --gold:#B8935A;--gold-light:#D4B07A;--white:#FDFCFA;
  --serif:'Cormorant Garamond',Georgia,serif;--sans:'DM Sans',system-ui,sans-serif;
}
html{scroll-behavior:smooth}
body{font-family:var(--sans);background:var(--cream);color:var(--ink);font-size:15px;line-height:1.7;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
img{max-width:100%;display:block}
.wrap{max-width:1200px;margin:0 auto;padding:0 5vw}
/* nav */
nav{position:sticky;top:0;z-index:50;display:flex;align-items:center;justify-content:space-between;height:64px;padding:0 5vw;background:rgba(245,241,235,.92);backdrop-filter:blur(12px);border-bottom:1px solid rgba(200,191,176,.4)}
.brand{font-family:var(--serif);font-size:1.5rem;letter-spacing:.02em;color:var(--ink)}
.brand b{color:var(--gold);font-weight:600}
.nav-links{display:flex;gap:1.5rem;font-size:.85rem;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-mid)}
.nav-links a:hover{color:var(--gold)}
@media(max-width:720px){.nav-links{display:none}}
/* breadcrumb */
.crumbs{padding:1.25rem 0 0;font-size:.82rem;color:var(--ink-light)}
.crumbs a:hover{color:var(--gold);text-decoration:underline}
.crumbs span{color:var(--stone-dark);margin:0 .4rem}
/* headings */
.eyebrow{font-size:.78rem;letter-spacing:.22em;text-transform:uppercase;color:var(--gold);margin-bottom:.9rem}
h1{font-family:var(--serif);font-weight:500;font-size:clamp(2rem,5vw,3.2rem);line-height:1.08;color:var(--ink);letter-spacing:-.01em}
h1 em{font-style:italic;color:var(--gold)}
h2{font-family:var(--serif);font-weight:500;font-size:clamp(1.5rem,3.4vw,2.2rem);line-height:1.15;color:var(--ink);margin:0 0 1rem}
.lead{font-size:1.02rem;color:var(--ink-mid);max-width:60ch;margin-top:1.1rem}
.section{padding:3rem 0}
/* stats row on cluster head */
.facts{display:flex;flex-wrap:wrap;gap:2.5rem;margin-top:1.8rem;padding-top:1.5rem;border-top:1px solid var(--stone)}
.fact .n{font-family:var(--serif);font-size:1.9rem;color:var(--gold);line-height:1}
.fact .l{font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-light);margin-top:.35rem}
/* card grid */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.6rem;margin-top:2rem}
.card{background:var(--white);border:1px solid rgba(200,191,176,.5);border-radius:2px;overflow:hidden;transition:box-shadow .3s,transform .3s;display:flex;flex-direction:column}
.card:hover{box-shadow:0 18px 40px -22px rgba(26,24,20,.45);transform:translateY(-3px)}
.card-img{position:relative;aspect-ratio:4/3;background:var(--cream-dark);overflow:hidden}
.card-img img{width:100%;height:100%;object-fit:cover;transition:transform .6s}
.card:hover .card-img img{transform:scale(1.04)}
.card-noimg{width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:var(--stone)}
.tag{position:absolute;top:.7rem;left:.7rem;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;padding:.25rem .6rem;border-radius:2px;background:var(--ink);color:var(--cream)}
.tag.hot{background:var(--gold)}
.card-b{padding:1.1rem 1.15rem 1.3rem;display:flex;flex-direction:column;flex:1}
.card-city{font-size:.76rem;letter-spacing:.08em;text-transform:uppercase;color:var(--gold)}
.card-t{font-family:var(--serif);font-size:1.25rem;line-height:1.2;margin:.35rem 0 .5rem;color:var(--ink)}
.card-meta{font-size:.83rem;color:var(--ink-light);margin-bottom:.9rem}
.card-price{margin-top:auto;font-family:var(--serif);font-size:1.4rem;color:var(--ink)}
.card-price sub{font-size:.62em;color:var(--ink-light)}
/* pills / related links */
.pills{display:flex;flex-wrap:wrap;gap:.55rem;margin-top:1.6rem}
.pill{border:1px solid var(--stone);color:var(--ink-mid);font-size:.85rem;padding:.4rem .85rem;border-radius:100px;transition:all .2s}
.pill:hover{border-color:var(--gold);color:var(--gold)}
/* SEO text block */
.prose{max-width:72ch;margin-top:1rem}
.prose p{margin:.9rem 0;color:var(--ink-mid)}
.prose h2{margin-top:2rem}
/* FAQ */
.faq{margin-top:1.4rem;border-top:1px solid var(--stone)}
.faq details{border-bottom:1px solid var(--stone);padding:.2rem 0}
.faq summary{cursor:pointer;list-style:none;padding:1rem 0;font-family:var(--serif);font-size:1.15rem;color:var(--ink);display:flex;justify-content:space-between;gap:1rem}
.faq summary::-webkit-details-marker{display:none}
.faq summary::after{content:'+';color:var(--gold);font-size:1.3rem}
.faq details[open] summary::after{content:'–'}
.faq .a{padding:0 0 1.1rem;color:var(--ink-mid);max-width:70ch}
/* ── object detail ── */
.obj{display:grid;grid-template-columns:1.15fr .85fr;gap:2.5rem;margin-top:1.5rem;align-items:start}
@media(max-width:860px){.obj{grid-template-columns:1fr}}
.gallery{display:flex;flex-direction:column;gap:.7rem}
.gal-main{aspect-ratio:4/3;background:var(--cream-dark);border-radius:2px;overflow:hidden}
.gal-main img{width:100%;height:100%;object-fit:cover}
.gal-thumbs{display:grid;grid-template-columns:repeat(auto-fill,minmax(72px,1fr));gap:.5rem}
.gal-thumbs img{aspect-ratio:1;object-fit:cover;border-radius:2px;border:1px solid rgba(200,191,176,.5)}
.plans-lbl{font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin:.4rem 0 .1rem}
.obj-side .place{font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;color:var(--gold)}
.obj-side h1{font-size:clamp(1.5rem,3.2vw,2rem);margin:.5rem 0 .8rem}
.price-row{display:flex;align-items:baseline;gap:.8rem;margin:.5rem 0 1.4rem}
.price-big{font-family:var(--serif);font-size:2rem;color:var(--ink)}
.deal{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;background:var(--cream-dark);color:var(--ink-mid);padding:.28rem .6rem;border-radius:2px}
.params{display:grid;grid-template-columns:1fr 1fr;gap:.05rem 1.5rem;border-top:1px solid var(--stone);padding-top:1.1rem}
.params .p{padding:.55rem 0;border-bottom:1px solid rgba(200,191,176,.4)}
.params .plbl{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-light)}
.params .pval{font-size:.95rem;color:var(--ink)}
.promo{margin-top:1.2rem;padding:1rem 1.1rem;background:rgba(184,147,90,.1);border:1px solid var(--gold-light);border-radius:2px;color:var(--ink-mid)}
.promo b{display:block;color:var(--gold);margin-bottom:.3rem}
.desc{margin-top:1.3rem;color:var(--ink-mid);max-width:70ch}
.feats-lbl{font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin:1.4rem 0 .6rem}
.feats{display:flex;flex-wrap:wrap;gap:.5rem}
.feat{font-size:.83rem;background:var(--cream-dark);color:var(--ink-mid);padding:.35rem .75rem;border-radius:100px}
.cta{display:flex;flex-wrap:wrap;gap:.6rem;margin-top:1.6rem}
.btn{display:inline-flex;align-items:center;gap:.45rem;font-size:.9rem;font-weight:500;padding:.7rem 1.15rem;border-radius:2px;border:1px solid transparent;cursor:pointer;transition:opacity .2s}
.btn:hover{opacity:.88}
.btn-wa{background:#25D366;color:#fff}
.btn-tg{background:#2AABEE;color:#fff}
.btn-max{background:var(--ink);color:var(--cream)}
.btn-call{background:var(--gold);color:#fff}
.btn-ghost{background:transparent;border-color:var(--stone);color:var(--ink-mid)}
/* footer */
footer{margin-top:4rem;background:var(--ink);color:var(--cream)}
.foot{max-width:1200px;margin:0 auto;padding:3rem 5vw;display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:2rem}
@media(max-width:720px){.foot{grid-template-columns:1fr}}
.foot .brand{color:var(--cream)}
.foot p{color:rgba(245,241,235,.6);font-size:.9rem;margin-top:.8rem;max-width:36ch}
.foot h4{font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin-bottom:.9rem}
.foot a{display:block;color:rgba(245,241,235,.7);font-size:.9rem;padding:.2rem 0}
.foot a:hover{color:var(--gold-light)}
.foot-links{display:flex;flex-wrap:wrap;gap:.1rem 1rem}
.copy{border-top:1px solid rgba(245,241,235,.12);padding:1.2rem 5vw;font-size:.8rem;color:rgba(245,241,235,.45);text-align:center}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">')


def json_ld(objs):
    out = []
    for o in objs:
        if o:
            out.append('<script type="application/ld+json">' +
                       json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "</script>")
    return "\n".join(out)


def page(*, title, description, canonical, body, jsonld=None, og_image=None,
         robots="index, follow, max-image-preview:large"):
    """Собирает полный HTML-документ."""
    og = ('<meta property="og:image" content="%s">' % esc_attr(og_image)) if og_image else ""
    tw_card = "summary_large_image" if og_image else "summary"
    tw_img = ('<meta name="twitter:image" content="%s">' % esc_attr(og_image)) if og_image else ""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc_attr(description)}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#F5F1EB">
<meta name="format-detection" content="telephone=yes">
<link rel="canonical" href="{esc_attr(canonical)}">
<link rel="alternate" hreflang="ru-RU" href="{esc_attr(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{esc_attr(title)}">
<meta property="og:description" content="{esc_attr(description)}">
<meta property="og:url" content="{esc_attr(canonical)}">
{og}
<meta name="twitter:card" content="{tw_card}">
<meta name="twitter:title" content="{esc_attr(title)}">
<meta name="twitter:description" content="{esc_attr(description)}">
{tw_img}
{FONTS}
<style>{CSS}</style>
{json_ld(jsonld or [])}
</head>
<body>
<nav>
  <a class="brand" href="{SITE_BASE}/">Horizon<b>Triel</b></a>
  <div class="nav-links">
    <a href="{SITE_BASE}/">Каталог</a>
    <a href="{MAIN_SITE}/#process">Как работаем</a>
    <a href="{MAIN_SITE}/#calc">Ипотека</a>
    <a href="{MAIN_SITE}/#contact">Контакты</a>
  </div>
</nav>
{body}
</body>
</html>"""


def breadcrumbs_html(items):
    """items: [(name, url|None), ...] последний — текущий (url None)."""
    parts = []
    for i, (name, url) in enumerate(items):
        if url:
            parts.append(f'<a href="{esc_attr(url)}">{esc(name)}</a>')
        else:
            parts.append(esc(name))
        if i < len(items) - 1:
            parts.append("<span>/</span>")
    return '<div class="wrap"><div class="crumbs">' + "".join(parts) + "</div></div>"


def _price_card(n):
    n = int(n or 0)
    if not n:
        return "Цена по запросу"
    if n >= 1_000_000:
        v = f"{n/1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{v} млн <sub>₽</sub>"
    if n >= 1000:
        return f"{round(n/1000):,}".replace(",", " ") + " тыс. <sub>₽</sub>"
    return f"{n:,}".replace(",", " ") + " <sub>₽</sub>"


def card(obj):
    """Карточка объекта в сетке. obj — dict из build.normalize(), с полем 'url'."""
    place = " · ".join([x for x in (obj.get("region"), obj.get("city")) if x])
    alt = " — ".join([x for x in (obj.get("title"), obj.get("type"), obj.get("region"), obj.get("city")) if x])
    imgs = obj.get("images") or []
    if imgs:
        img = f'<img src="{esc_attr(imgs[0])}" alt="{esc_attr(alt)}" loading="lazy" decoding="async">'
    else:
        img = ('<div class="card-noimg"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" '
               'stroke="currentColor" stroke-width="1.3"><rect x="3" y="3" width="18" height="18" rx="2"/>'
               '<circle cx="9" cy="9" r="2"/><path d="M21 15l-5-5L5 21"/></svg></div>')
    tag = ""
    if obj.get("tag") == "new":
        tag = '<span class="tag">Новое</span>'
    elif obj.get("tag") == "hot":
        tag = '<span class="tag hot">Топ</span>'
    meta_bits = []
    if obj.get("residential_complex"): meta_bits.append("ЖК " + str(obj["residential_complex"]))
    if obj.get("area"): meta_bits.append(f'{obj["area"]} м²')
    if obj.get("rooms"): meta_bits.append(f'{obj["rooms"]} комн.')
    if obj.get("land"): meta_bits.append(f'{obj["land"]} сот.')
    if obj.get("floors"): meta_bits.append(f'{obj["floors"]} эт.')
    meta = " · ".join(meta_bits)
    return (
        f'<a class="card" href="{esc_attr(obj["url"])}">'
        f'<div class="card-img">{img}{tag}</div>'
        f'<div class="card-b">'
        f'<div class="card-city">{esc(place)}</div>'
        f'<div class="card-t">{esc(obj.get("title") or "Объект недвижимости")}</div>'
        + (f'<div class="card-meta">{esc(meta)}</div>' if meta else "")
        + f'<div class="card-price">{_price_card(obj.get("price"))}</div>'
        f'</div></a>'
    )


def footer(settings, seo_links):
    """seo_links: [(label, url), ...] для нижнего блока перелинковки."""
    tel = settings.get("tel", "")
    tel_href = "".join(c for c in tel if c.isdigit() or c == "+")
    links_html = "".join(f'<a href="{esc_attr(u)}">{esc(l)}</a>' for l, u in seo_links)
    return f"""
<footer>
  <div class="foot">
    <div>
      <a class="brand" href="{SITE_BASE}/">Horizon<b>Triel</b></a>
      <p>Подбор, проверка и сопровождение сделок с недвижимостью по всей России — квартиры, дома, участки, гаражи и коммерческие объекты.</p>
    </div>
    <div>
      <h4>Связь</h4>
      <a href="tel:{esc_attr(tel_href)}">{esc(tel)}</a>
      <a href="https://wa.me/{esc_attr(settings.get('wa',''))}" target="_blank" rel="noopener">WhatsApp</a>
      <a href="{esc_attr(settings.get('tg',''))}" target="_blank" rel="noopener">Telegram</a>
      {'<a href="%s" target="_blank" rel="noopener">MAX</a>' % esc_attr(settings.get('max','')) if settings.get('max') else ''}
      <a href="mailto:{esc_attr(settings.get('email',''))}">{esc(settings.get('email',''))}</a>
    </div>
    <div>
      <h4>Направления</h4>
      <div class="foot-links">{links_html}</div>
    </div>
  </div>
  <div class="copy">© {BRAND}. Недвижимость по России. Информация на сайте не является публичной офертой.</div>
</footer>"""
