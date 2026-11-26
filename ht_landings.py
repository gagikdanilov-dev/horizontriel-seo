# -*- coding: utf-8 -*-
"""Four distinct, one-page regional service landings for Horizontriel.

Called by the existing SEO generator only after stable object URLs are loaded.
Never changes PocketBase, existing listing URLs, CNAME, or other pages.
"""
from __future__ import annotations

from datetime import date
from html import escape
import json
import re
from urllib.parse import urlencode

from config import BRAND, fmt_price_plain
from listing_contract import newest_first
from templates import listing_date_html


CAMPAIGNS = [
    {
        'type': 'Квартира', 'slug': 'podbor-kvartir',
        'label': 'Квартиры', 'eyebrow': 'КВАРТИРЫ · КАВКАЗСКИЕ МИНЕРАЛЬНЫЕ ВОДЫ',
        'title': 'Подберём квартиру в Кисловодске и на КМВ',
        'page_title': f'Подбор квартиры в Кисловодске и на КМВ | {BRAND}',
        'description': 'Подбор квартиры в Кисловодске и городах КМВ по бюджету, планировке и району. Сравним актуальные предложения и поможем проверить документы.',
        'lead': 'Не нужно просматривать сотни вариантов. Начнём с вашего бюджета и сценария покупки: для жизни, переезда или инвестиций. Подготовим короткий список актуальных квартир с понятными условиями.',
        'hero_bottom': 'Район · планировка · состояние · юридическая проверка',
        'intro': 'Выбираем квартиру не только по стоимости квадратного метра. Сравниваем инфраструктуру, этаж, планировку, состояние дома и расходы после покупки. Для переезда учитываем транспорт, школы и близость к нужным услугам.',
        'what': [
            ('Проверим бюджет', 'Учитываем первоначальный взнос, возможные расходы на ремонт и оформление, а не только цену объявления.'),
            ('Сравним планировки', 'Обсудим комнаты, кухню, этаж, лифт и реальную пригодность пространства для вашей семьи.'),
            ('Разберём документы', 'Обозначим, какие документы и ограничения нужно проверить до аванса и сделки.'),
        ],
        'questions': [
            ('Можно подобрать квартиру под конкретный район?', 'Да. Укажите город, район, бюджет и обязательные требования — подбор начнём с них.'),
            ('Поможете оценить расходы после покупки?', 'При выборе учитываем возможный ремонт, оформление и регулярные расходы. Окончательные суммы уточняются по конкретному объекту.'),
            ('Как понять, что объявление ещё актуально?', 'В подборке используем текущие опубликованные предложения и уточняем доступность перед показом.'),
        ],
        'category_path': '/kvartiry/',
        'step2': 'Сопоставим планировки, районы, состояние квартир и варианты финансирования.',
    },
    {
        'type': 'Дом', 'slug': 'podbor-domov',
        'label': 'Дома', 'eyebrow': 'ДОМА И КОТТЕДЖИ · КМВ',
        'title': 'Дом на КМВ — с понятными условиями покупки',
        'page_title': f'Подбор дома в Кисловодске и на КМВ | {BRAND}',
        'description': 'Подберём дом в Кисловодске, Ессентуках и на КМВ. Сопоставим участок, подъезд, коммуникации, состояние здания и документы.',
        'lead': 'Красивый фасад — только начало. Поможем сравнить реальные дома по участку, конструктиву, коммуникациям, подъезду и юридическим условиям, чтобы после покупки не появились неприятные сюрпризы.',
        'hero_bottom': 'Участок · коммуникации · подъезд · состояние дома',
        'intro': 'При покупке частного дома нужно проверить больше, чем при покупке квартиры. Важны назначение участка, границы, подъездные пути, водоснабжение, отопление, канализация и качество строительства. Эти параметры обсуждаем до выезда на просмотр.',
        'what': [
            ('Дом и участок', 'Сопоставим площадь дома, размер участка, назначение земли и удобство размещения на территории.'),
            ('Коммуникации', 'Уточним подключение к сетям, тип отопления, воду, канализацию и доступность обслуживания.'),
            ('Проверка сделки', 'Поможем составить список документов на дом и землю, подлежащих проверке до внесения аванса.'),
        ],
        'questions': [
            ('Сможете подобрать дом с определённой площадью участка?', 'Да. Можно указать минимальную площадь земли и дома, город, район и бюджет.'),
            ('Как проверить коммуникации?', 'По конкретному объекту уточняют технические условия, фактические подключения и договоры. Данные из объявления отдельно перепроверяются.'),
            ('Подходит ли дом для круглогодичного проживания?', 'Это зависит от отопления, утепления, инженерных сетей и состояния здания. Перед покупкой оценим эти вопросы по выбранным вариантам.'),
        ],
        'category_path': '/doma/',
        'step2': 'Проверим параметры участка, подъезд, инженерные сети и состояние здания.',
    },
    {
        'type': 'Земля', 'slug': 'podbor-uchastkov',
        'label': 'Участки', 'eyebrow': 'ЗЕМЕЛЬНЫЕ УЧАСТКИ · КМВ',
        'title': 'Найдём участок для строительства на КМВ',
        'page_title': f'Подбор земельного участка в Кисловодске и на КМВ | {BRAND}',
        'description': 'Подбор участков под строительство в Кисловодске и на КМВ: назначение земли, подъезд, коммуникации, границы и рельеф.',
        'lead': 'Для участка критичны документы, разрешённое использование, рельеф и подключение коммуникаций. Подберём предложения под вашу задачу и поможем определить, что проверить до сделки.',
        'hero_bottom': 'Назначение земли · границы · рельеф · коммуникации',
        'intro': 'Участок с красивым видом не всегда подходит для строительства. Важно проверить категорию и вид разрешённого использования земли, границы, ограничения, сервитуты и стоимость подключения инженерных сетей. Все эти критерии влияют на пригодность участка.',
        'what': [
            ('Назначение участка', 'Сверим заявленные цели использования с документами и градостроительными ограничениями.'),
            ('Рельеф и подъезд', 'Обсудим уклон, геометрию участка, доступность дороги и возможные дополнительные работы.'),
            ('Сети и документы', 'Уточним доступность воды, электричества, газа и перечень юридических проверок.'),
        ],
        'questions': [
            ('Какую площадь участка выбрать?', 'Зависит от проекта дома, расположения построек и бюджета. Начнём с минимальной площади и требований к форме участка.'),
            ('Можно ли строить на любом участке?', 'Нет. Возможность строительства зависит от категории земли, разрешённого использования и ограничений территории.'),
            ('Есть ли смысл смотреть участок без коммуникаций?', 'Иногда — да, но сначала нужно оценить техническую доступность подключения и дополнительные затраты.'),
        ],
        'category_path': '/uchastki/',
        'step2': 'Сверим назначение, рельеф, подъезд, границы и возможные ограничения.',
    },
    {
        'type': 'Коммерция', 'slug': 'podbor-kommercheskoy',
        'label': 'Коммерция', 'eyebrow': 'КОММЕРЧЕСКАЯ НЕДВИЖИМОСТЬ · КМВ',
        'title': 'Подберём помещение под ваш бизнес',
        'page_title': f'Подбор коммерческой недвижимости на КМВ | {BRAND}',
        'description': 'Подбор коммерческой недвижимости на КМВ: помещения под офис, торговлю и услуги. Сравним назначение, локацию, входную группу и условия сделки.',
        'lead': 'Помещение должно работать на вашу бизнес-модель. Сопоставим локацию, вход, планировку, назначение, технические возможности и общую стоимость владения, а не только цену квадратного метра.',
        'hero_bottom': 'Назначение · доступ · трафик · инженерия',
        'intro': 'Коммерческий объект оцениваем с учётом будущего использования. Удобство посетителей, отдельный вход, доступность парковки, электромощность, ограничения по эксплуатации и возможный ремонт могут оказаться важнее разницы в стоимости.',
        'what': [
            ('Под задачу бизнеса', 'Сначала определяем формат работы, необходимую площадь, планировку и допустимые ограничения.'),
            ('Локация и доступ', 'Сравним транспорт, видимость помещения, входную группу и условия для клиентов и сотрудников.'),
            ('Расходы и риски', 'Обсудим технические условия, расходы на адаптацию и документы на объект.'),
        ],
        'questions': [
            ('Поможете найти помещение с отдельным входом?', 'Да. Зафиксируем требование к входной группе и отберём подходящие опубликованные варианты.'),
            ('Как оценить помещение под конкретный бизнес?', 'Начнём с назначения, потока посетителей, планировки и технических требований. Для окончательного решения потребуется проверка объекта.'),
            ('Можно сравнить варианты в нескольких городах?', 'Да. Подбор возможен по Кисловодску, Ессентукам, Пятигорску и другим городам КМВ при наличии предложений.'),
        ],
        'category_path': '/kommercheskaya-nedvizhimost/',
        'step2': 'Проверим локацию, назначение помещения и затраты на адаптацию.',
    },
]

CSS = r'''
:root{--bg:#faf8f4;--ink:#142120;--ink2:#42504c;--accent:#b99b61;--card:#fff;--line:#e5dfd3;--muted:#efe9de}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.58 system-ui,-apple-system,"Segoe UI",Arial,sans-serif}
a{color:inherit}a:focus-visible,button:focus-visible{outline:3px solid #bd954e;outline-offset:3px}
.wrap{width:min(1180px,calc(100% - 40px));margin-inline:auto}
header{background:#12201e;color:#f8f4ec;border-bottom:1px solid #3a4540}
.bar{display:flex;align-items:center;justify-content:space-between;gap:18px;min-height:76px}.brand{font-weight:800;text-decoration:none;letter-spacing:-.035em;font-size:clamp(1.35rem,2.3vw,1.7rem)}
.nav{display:flex;gap:16px;align-items:center;font-size:.9rem}.nav a{text-decoration:none}.nav a:hover{text-decoration:underline}
.hero{background:radial-gradient(ellipse at 100% 12%,#46584a 0,transparent 47%),linear-gradient(135deg,#12201e 0%,#1e3029 100%);color:#faf5ed;padding:78px 0 86px}
.hero-grid{display:grid;grid-template-columns:1.38fr .68fr;gap:60px;align-items:center}.kicker{font-size:.74rem;letter-spacing:.17em;color:#ddc492;font-weight:750;text-transform:uppercase}
h1{font-weight:640;letter-spacing:-.05em;line-height:1.09;font-size:clamp(2.3rem,5.7vw,5rem);margin:17px 0 25px}h2{font-size:clamp(1.7rem,3.1vw,2.65rem);line-height:1.17;letter-spacing:-.034em;margin:8px 0 19px}h3{font-size:1.15rem;margin:0 0 8px}
.hero p{color:#e6e4d9;max-width:60ch;font-size:1.1rem}.actions{display:flex;flex-wrap:wrap;gap:12px;margin:32px 0 19px}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:51px;padding:12px 20px;border-radius:8px;text-align:center;font-weight:700;text-decoration:none;transition:transform .18s,background .18s;border:1px solid transparent}.btn:hover{transform:translateY(-2px)}.gold{background:#d9b779;color:#14211f}.gold:hover{background:#e5c896}.ghost{border-color:#75827b;color:#fff}.white{background:#1d322d;color:#fff}
.sublabel{font-size:.84rem;color:#c8c7bf}.hero-panel{border:1px solid #7c877d;border-radius:18px;padding:28px;background:rgba(255,255,255,.075);box-shadow:0 22px 50px #0c171425}
.hero-panel p{font-size:1.02rem}.hero-panel strong{font-size:1.13rem}.fine{font-size:.84rem;color:#bfc8c0}
section{padding:78px 0}.section-sub{max-width:810px;color:var(--ink2);font-size:1.04rem;margin-bottom:28px}
.three{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:17px}.tile{background:#fff;border:1px solid var(--line);padding:25px;border-radius:12px}.tile .count{color:#9b7c43;font-weight:800;letter-spacing:.07em;font-size:.83rem}
.muted{background:#f0ede7}.offers{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:17px}.offer{display:block;border-radius:13px;background:white;border:1px solid var(--line);overflow:hidden;text-decoration:none;transition:box-shadow .2s,transform .2s}.offer:hover{transform:translateY(-3px);box-shadow:0 12px 25px #192b261b}
.photo{display:block;width:100%;height:200px;object-fit:cover;background:linear-gradient(120deg,#869b8d,#384f44)}.offer-copy{padding:18px}.offer-copy h3{font-size:1.02rem;min-height:3.1em}.price{font-size:1.3rem;font-weight:800;letter-spacing:-.02em}.details{color:#526159;font-size:.87rem}.tagline{font-size:.9rem;color:#64716a}
.steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px}.step{border-top:1px solid #b99b61;padding-top:17px}.step b{font-size:1.38rem;color:#967446}
.questions{max-width:930px}details{background:#fff;border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:10px}summary{cursor:pointer;font-weight:650}details p{color:var(--ink2);margin-bottom:1px}
.callout{padding:50px 0 65px;background:#172923;color:#fff}.callout h2{color:#fff}.callout p{color:#cad3cb;max-width:750px}footer{background:#101b18;color:#b8c3ba;padding:28px 0;font-size:.85rem}footer a{color:inherit}.foot{display:flex;justify-content:space-between;flex-wrap:wrap;gap:14px}
.small-caps{letter-spacing:.12em;text-transform:uppercase;font-size:.76rem;color:#997749;font-weight:750}
.listing-date{display:block;font-size:.82rem;color:#526159;margin:.6rem 0}
@media(max-width:850px){.hero-grid{grid-template-columns:1fr;gap:25px}.hero{padding:55px 0}.three,.offers{grid-template-columns:repeat(2,minmax(0,1fr))}.steps{grid-template-columns:1fr}.nav a:nth-child(2){display:none}}
@media(max-width:600px){.wrap{width:min(100% - 28px,1180px)}section{padding:48px 0}.bar{min-height:68px}.nav{gap:8px}.nav a:not(:last-child){display:none}.three,.offers{grid-template-columns:1fr}.hero-panel{padding:20px}.btn{width:100%}.offer-copy h3{min-height:0}.actions{flex-direction:column}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.btn,.offer{transition:none}}
'''


def e(v):
    return escape(str(v or ''), quote=True)


def valid_phone(raw):
    digits = re.sub(r'[^0-9+]', '', str(raw or ''))
    return digits if digits and len(re.sub(r'\D', '', digits)) >= 10 else '+79054188095'


def render(obj, selected, C, settings):
    selected = newest_first(selected)
    slug = obj['slug']
    base = C.SITE_BASE.rstrip('/')
    canonical = f'{base}/lp/{slug}/'
    target = C.MAIN_SITE.rstrip('/')
    brand = e(BRAND)
    # Preserve the landing marker even if the visitor has JavaScript disabled.
    # The main Tilda form already records utm_content in PocketBase leads.source.
    lead_url = target + '/?' + urlencode({'ht_lp': slug, 'utm_content': 'lp_' + slug}) + '#contact'
    inventory_url = base + obj['category_path']
    tel = str(settings.get('tel') or '+7 905 418 80 95')
    tel_url = 'tel:' + valid_phone(tel)
    site_desc = obj['description']
    cards = []
    for item in selected[:6]:
        link = base + str(item.get('url') or '')
        images = item.get('images') or []
        img_src = images[0] if isinstance(images, list) and images else ''
        image = (f'<img class="photo" src="{e(img_src)}" alt="Фото объекта: {e(item.get("title") or obj["label"])}" loading="lazy" decoding="async">'
                 if img_src and str(img_src).startswith('https://') else '<div class="photo" aria-hidden="true"></div>')
        city = e(item.get('city') or 'КМВ')
        title = e(item.get('title') or obj['label'])
        price_html = f'<div class="price">{e(fmt_price_plain(item.get("price"), item.get("currency")))}</div>'
        area = item.get('area')
        area_text = f' · {e(area)} м²' if area and obj['type'] != 'Земля' else ''
        cards.append(f'<a class="offer" href="{e(link)}" aria-label="{title}: подробнее">{image}<div class="offer-copy"><span class="details">{city}{area_text}</span><h3>{title}</h3>{price_html}{listing_date_html(item)}<span class="tagline">Смотреть объект →</span></div></a>')
    offers = ''.join(cards)
    if not offers:
        offers = f'<div class="tile">В каталоге пока нет опубликованных предложений этого типа. Оставьте запрос на подбор — обсудим вашу задачу и проверим доступные варианты.</div>'

    benefits = ''.join(f'<div class="tile"><span class="count">0{i}</span><h3>{e(h)}</h3><p>{e(t)}</p></div>' for i,(h,t) in enumerate(obj['what'],1))
    faqs = ''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q,a in obj['questions'])
    steps = [('Заявка', 'Вы сообщаете город, бюджет, сроки и обязательные требования.'),
             ('Подбор', obj['step2']),
             ('Просмотр и сделка', 'Согласуем просмотр выбранных вариантов и дальнейшие шаги после проверки условий.')]
    step_html = ''.join(f'<div class="step"><b>0{i}</b><h3>{e(h)}</h3><p>{e(t)}</p></div>' for i,(h,t) in enumerate(steps,1))
    linked = [{'@type':'ListItem','position':i+1,'url':base + s['url'],'name':str(s.get('title') or obj['label'])} for i,s in enumerate(selected[:6]) if s.get('url')]
    ld = {
        '@context': 'https://schema.org',
        '@graph': [
            {'@type':'RealEstateAgent','@id':target+'/#real-estate-agent','name':BRAND,'url':target+'/','telephone':tel,'email':str(settings.get('email') or 'horizontriel@gmail.com'),'areaServed':{'@type':'AdministrativeArea','name':'Кавказские Минеральные Воды'}},
            {'@type':'Service','name':obj['page_title'].split(' | ')[0], 'description':site_desc,'provider':{'@id':target+'/#real-estate-agent'},'areaServed':'Кавказские Минеральные Воды','url':canonical},
            {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Каталог','item':base+'/'},{'@type':'ListItem','position':2,'name':obj['label'],'item':canonical}]},
        ]
    }
    if linked:
        ld['@graph'].append({'@type':'ItemList','name':'Актуальные объекты: '+obj['label'].lower(),'itemListElement':linked})
    ld_json = json.dumps(ld, ensure_ascii=False, separators=(',',':')).replace('<','\\u003c')
    robots = 'index,follow,max-image-preview:large' if selected else 'noindex,follow'
    n = len(selected)
    inventory = f'Опубликованных предложений в подборке: {n}' if n else 'Подбор под ваш запрос'
    footer_email = e(settings.get('email') or 'horizontriel@gmail.com')
    html = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(obj['page_title'])}</title><meta name="description" content="{e(site_desc)}"><meta name="robots" content="{robots}">
<link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:site_name" content="{brand}"><meta property="og:title" content="{e(obj['page_title'])}"><meta property="og:description" content="{e(site_desc)}"><meta property="og:url" content="{e(canonical)}">
<meta name="theme-color" content="#12201e"><style>{CSS}</style><script type="application/ld+json">{ld_json}</script></head>
<body><header><div class="bar wrap"><a class="brand" href="{e(target)}/" aria-label="{brand} — на главную">{brand}</a><nav class="nav" aria-label="Основная навигация"><a href="{e(inventory_url)}">Каталог объектов</a><a href="#kak-rabotaem">Как работаем</a><a href="{e(tel_url)}">{e(tel)}</a></nav></div></header>
<main><section class="hero"><div class="wrap hero-grid"><div><div class="kicker">{e(obj['eyebrow'])}</div><h1>{e(obj['title'])}</h1><p>{e(obj['lead'])}</p><div class="actions"><a class="btn gold" href="{e(lead_url)}" data-ht-event="lead">Получить подборку объектов</a><a class="btn ghost" href="{e(inventory_url)}" data-ht-event="catalog">Посмотреть предложения</a></div><div class="sublabel">{e(obj['hero_bottom'])}</div></div>
<aside class="hero-panel"><div class="small-caps">Актуальный каталог</div><h2>{e(obj['label'])} на КМВ</h2><p>{e(inventory)}</p><p>Предложения берём из действующего каталога. Доступность уточняется перед просмотром.</p><a class="btn gold" href="{e(inventory_url)}">Открыть каталог</a></aside></div></section>
<section><div class="wrap"><div class="small-caps">Подбор по вашим критериям</div><h2>На что обращаем внимание</h2><p class="section-sub">{e(obj['intro'])}</p><div class="three">{benefits}</div></div></section>
<section class="muted" id="predlozheniya"><div class="wrap"><div class="small-caps">Из актуального каталога</div><h2>Варианты, с которых можно начать</h2><p class="section-sub">Это примеры опубликованных объектов, а не гарантия наличия. Нажмите на карточку, чтобы увидеть фото и параметры.</p><div class="offers">{offers}</div><div class="actions"><a class="btn white" href="{e(inventory_url)}">Все объекты категории</a><a class="btn white" href="{e(lead_url)}" data-ht-event="lead">Подобрать под бюджет</a></div></div></section>
<section id="kak-rabotaem"><div class="wrap"><div class="small-caps">Три понятных шага</div><h2>От запроса до просмотра</h2><div class="steps">{step_html}</div></div></section>
<section class="muted"><div class="wrap questions"><div class="small-caps">Ответы перед покупкой</div><h2>Частые вопросы</h2>{faqs}</div></section>
<section class="callout" id="svyaz"><div class="wrap"><div class="small-caps">Подбор недвижимости</div><h2>Расскажите, какой объект ищете</h2><p>Город, бюджет и два-три важных критерия — этого достаточно, чтобы начать разговор. Никаких обязательств до обсуждения условий.</p><div class="actions"><a class="btn gold" href="{e(lead_url)}" data-ht-event="lead">Оставить заявку</a><a class="btn ghost" href="{e(tel_url)}" data-ht-event="phone">Позвонить: {e(tel)}</a></div></div></section></main>
<footer><div class="wrap foot"><div>© {date.today().year} {brand}. Недвижимость на КМВ.<br>Информация не является публичной офертой.</div><div><a href="{e(target)}/">Главный сайт</a> · <a href="{e(inventory_url)}">{e(obj['label'])}</a> · <a href="mailto:{footer_email}">{footer_email}</a></div></div></footer>
<script>(function(m,d,t,u,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();k=d.createElement(t),a=d.getElementsByTagName(t)[0];k.async=1;k.src=u;a.parentNode.insertBefore(k,a)}})(window,document,'script','https://mc.yandex.ru/metrika/tag.js','ym');ym(110255493,'init',{{clickmap:true,trackLinks:true,accurateTrackBounce:true}});</script>
<script>(function(){{var keep=['utm_source','utm_medium','utm_campaign','utm_term','utm_content','yclid'];document.querySelectorAll('a[data-ht-event]').forEach(function(a){{if(a.dataset.htEvent==='lead'){{try{{var u=new URL(a.href);var incoming=new URLSearchParams(location.search);keep.forEach(function(k){{if(incoming.has(k))u.searchParams.set(k,incoming.get(k))}});var marker='lp_{slug}';var content=(u.searchParams.get('utm_content')||'').trim();if(content!==marker && !content.endsWith('__'+marker)){{var prefix=content.slice(0,Math.max(0,80-marker.length-2));u.searchParams.set('utm_content',prefix?prefix+'__'+marker:marker)}}a.href=u.toString()}}catch(_e){{}}}}a.addEventListener('click',function(){{try{{ym(110255493,'reachGoal','ht_landing_click',{{section:'{slug}',action:a.dataset.htEvent}})}}catch(_e){{}}}})}})}})();</script>
</body></html>'''
    return html


def build_landings(C, objs, settings, write_page):
    """Generate distinct one-pagers after record URL finalization, before sitemap.

    `write_page(path, html, urls, index)` appends to the existing catalogue sitemap.
    """
    result = []
    for spec in CAMPAIGNS:
        selected = [o for o in objs if o.get('type') == spec['type'] and o.get('id') and o.get('url')]
        selected = newest_first(selected)
        path = f"/lp/{spec['slug']}/"
        html = render(spec, selected, C, settings)
        write_page(path, html, result, index=bool(selected))
        print(f"• посадочная страница {path}: {len(selected)} объявлений, index={bool(selected)}")
    return result
