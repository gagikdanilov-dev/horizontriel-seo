# -*- coding: utf-8 -*-
"""
Конфигурация генератора статических SEO-страниц HorizonTriel.
Всё, что нужно менять при переносе, — здесь.
"""
import os

# ── Источник данных (PocketBase) ──
PB_URL      = os.environ.get("PB_URL", "https://api.horizontriel.com").rstrip("/")
PB_COLLECTION = os.environ.get("PB_COLLECTION", "listings")
PB_SETTINGS = os.environ.get("PB_SETTINGS", "site_settings")

# ── Где будет жить статический сайт ──
# ВАЖНО: это отдельный адрес от Тильды. Рекомендуется поддомен на GitHub Pages,
# например https://catalog.horizontriel.com  (см. README, раздел «Домен»).
SITE_BASE = os.environ.get("SITE_BASE", "https://catalog.horizontriel.com").rstrip("/")

# Главный сайт (Тильда) — на него ссылаемся из шапки/футера
MAIN_SITE = os.environ.get("MAIN_SITE", "https://horizontriel.com").rstrip("/")

BRAND = "HorizonTriel"
OUT_DIR = os.environ.get("OUT_DIR", "dist")

# Резервные контакты, если site_settings недоступны
FALLBACK_SETTINGS = {
    "tel":   "+7 905 412 7314",
    "wa":    "79054127314",
    "tg":    "https://t.me/mikhail_korolev1977",
    "max":   "https://max.ru/join/ypfQ0KRhQbnEeNU-M-qs1czsE97KJd6C6Yg-2R9_tIQ",
    "email": "horizontriel@gmail.com",
}

# ── Транслитерация RU → lat для человекочитаемых URL ──
_TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}

def slugify(text):
    """Кириллица/латиница → безопасный slug: nizhniy-novgorod, rostov-na-donu."""
    if not text:
        return ""
    text = str(text).strip().lower()
    out = []
    for ch in text:
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ch.isalnum() and ch.isascii():
            out.append(ch)
        elif ch in (" ", "-", "_", "/", ".", ",", "«", "»", "'", '"'):
            out.append("-")
        # прочие символы отбрасываем
    s = "".join(out)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")

# ── Типы недвижимости: значение в PB → метаданные для URL/заголовков/текста ──
# gen  — винительный падеж для «Купить {gen}»
# genpl — родительный мн. для счётчика «{n} {genpl}»
TYPE_META = {
    "Квартира":    {"slug": "kvartiry",                    "plural": "Квартиры",                 "gen": "квартиру",                "genpl": "квартир"},
    "Апартаменты": {"slug": "apartamenty",                 "plural": "Апартаменты",              "gen": "апартаменты",             "genpl": "апартаментов"},
    "Дом":         {"slug": "doma",                        "plural": "Дома",                     "gen": "дом",                     "genpl": "домов"},
    "Таунхаус":    {"slug": "taunhausy",                   "plural": "Таунхаусы",                "gen": "таунхаус",                "genpl": "таунхаусов"},
    "Дуплекс":     {"slug": "dupleksy",                    "plural": "Дуплексы",                 "gen": "дуплекс",                 "genpl": "дуплексов"},
    "Коммерция":   {"slug": "kommercheskaya-nedvizhimost", "plural": "Коммерческая недвижимость","gen": "коммерческую недвижимость","genpl": "объектов"},
    "Гараж":       {"slug": "garazhi",                     "plural": "Гаражи",                   "gen": "гараж",                   "genpl": "гаражей"},
    "Земля":       {"slug": "uchastki",                    "plural": "Земельные участки",        "gen": "участок",                 "genpl": "участков"},
}

# Приоритетные направления = ссылки в подвале главной. Для них страница создаётся
# ВСЕГДА (даже без объектов), чтобы ссылки не давали 404. Пустые → noindex, вне sitemap.
PRIORITY_TYPES = ["Квартира", "Дом", "Земля", "Гараж", "Коммерция", "Апартаменты", "Таунхаус", "Дуплекс"]
PRIORITY_CITIES = ["Москва", "Санкт-Петербург", "Краснодар", "Сочи", "Анапа", "Геленджик",
                   "Кисловодск", "Пятигорск", "Ессентуки", "Ставрополь", "Ростов-на-Дону",
                   "Казань", "Екатеринбург", "Новосибирск", "Нижний Новгород", "Самара",
                   "Уфа", "Воронеж", "Пермь", "Калининград"]
PRIORITY_REGIONS = ["Краснодарский край", "Ставропольский край", "Московская область", "Крым"]

# Предложный падеж для основных городов («в Кисловодске»). Для остальных — «в городе X».
CITY_PREP = {
    "Москва": "в Москве", "Санкт-Петербург": "в Санкт-Петербурге", "Краснодар": "в Краснодаре",
    "Сочи": "в Сочи", "Анапа": "в Анапе", "Геленджик": "в Геленджике", "Кисловодск": "в Кисловодске",
    "Пятигорск": "в Пятигорске", "Ессентуки": "в Ессентуках", "Ставрополь": "в Ставрополе",
    "Ростов-на-Дону": "в Ростове-на-Дону", "Казань": "в Казани", "Екатеринбург": "в Екатеринбурге",
    "Новосибирск": "в Новосибирске", "Нижний Новгород": "в Нижнем Новгороде", "Самара": "в Самаре",
    "Уфа": "в Уфе", "Воронеж": "в Воронеже", "Пермь": "в Перми", "Калининград": "в Калининграде",
    "Минеральные Воды": "в Минеральных Водах", "Железноводск": "в Железноводске",
}

def city_prep(city):
    return CITY_PREP.get(city, f"в городе {city}") if city else ""

def region_prep(region):
    # Для регионов достаточно «в {регион}» — работает для «крае/области/Крыму» через словарь
    m = {"Краснодарский край": "в Краснодарском крае", "Ставропольский край": "в Ставропольском крае",
         "Московская область": "в Московской области", "Ростовская область": "в Ростовской области",
         "Крым": "в Крыму", "Республика Крым": "в Крыму"}
    return m.get(region, f"в регионе «{region}»") if region else ""

def type_meta(t):
    return TYPE_META.get(t, {"slug": slugify(t) or "obekty", "plural": t or "Объекты",
                             "gen": (t or "объект").lower(), "genpl": "объектов"})

# Русский счётчик: 1 объект / 2 объекта / 5 объектов
def plural_ru(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return few
    return many

def fmt_price_plain(n):
    n = int(n or 0)
    if not n:
        return "Цена по запросу"
    if n >= 1_000_000:
        v = f"{n/1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{v} млн ₽"
    if n >= 1000:
        return f"{round(n/1000):,}".replace(",", " ") + " тыс. ₽"
    return f"{n:,}".replace(",", " ") + " ₽"

def fmt_num(n):
    try:
        return f"{int(n):,}".replace(",", " ")
    except Exception:
        return str(n)
