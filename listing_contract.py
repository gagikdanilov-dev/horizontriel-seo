"""Public listing contract shared by the static catalog and its landing pages.

No network access or database writes. Unknown data stays unknown: an unqualified
foreign price is not RUB, and a record's creation date is not its publication.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import quote, urlsplit

import config as C


COUNTRY_CODES = {"Россия": "RU", "Кипр": "CY", "Турция": "TR", "ОАЭ": "AE", "Испания": "ES"}
COUNTRY_ALIASES = {
    "Россия": ("ru", "rus", "russia", "россия", "российская федерация"),
    "Кипр": ("cy", "cyp", "cyprus", "кипр"),
    "Турция": ("tr", "tur", "turkey", "türkiye", "турция"),
    "ОАЭ": ("ae", "are", "uae", "united arab emirates", "оаэ", "объединённые арабские эмираты", "объединенные арабские эмираты", "дубай", "dubai"),
    "Испания": ("es", "esp", "spain", "españa", "испания"),
}
_COUNTRIES = {alias.casefold(): label for label, aliases in COUNTRY_ALIASES.items() for alias in aliases}
# One observed legacy spelling; do not infer countries from arbitrary region/city names.
LEGACY_RUSSIAN_REGION = "Ставропольский"


def clean(value):
    return " ".join(str(value or "").split())


def complex_label(value):
    title = str(value or "").strip()
    if not title or re.match(r"^жк(?=$|[\s«»\"'“”„(])", title, re.I):
        return title
    return "ЖК " + title


def basement_floor(obj):
    source = str(obj.get("desc") or obj.get("description") or "")
    return bool(re.search(r"(?:^|[.!?\n])\s*цокольный этаж\s*(?=[.!?]|$)", source, re.I))


def is_recent_listing(obj, now=None):
    stamp, _ = listing_date(obj)
    if stamp is None:
        return False
    days = ((now or datetime.now(timezone.utc)) - stamp).total_seconds() / 86400
    return 0 <= days <= 30


def country_for(obj):
    explicit = clean(obj.get("country"))
    if explicit:
        return _COUNTRIES.get(explicit.casefold(), explicit)
    region = clean(obj.get("region"))
    if region.casefold() in {C.SEO_REGION.casefold(), LEGACY_RUSSIAN_REGION.casefold()}:
        return "Россия"
    # Older records sometimes store the country in region. Retain region in the
    # normalized record so existing filters and links continue to match it.
    return _COUNTRIES.get(region.casefold(), "")


def currency_for(obj):
    raw = clean(obj.get("currency")).upper()
    if raw:
        return raw if raw in C.CURRENCY_LABELS else None
    # Normalization deliberately removes an unsupported code from currency.
    # Preserve its presence so a second pass cannot mistake it for legacy data.
    if obj.get("_currency_explicit"):
        return None
    return "RUB" if country_for(obj) == "Россия" else None


def normalize_price(value):
    if isinstance(value, bool):
        return 0
    try:
        amount = Decimal(str(value or 0))
        if not amount.is_finite() or amount <= 0:
            return 0
        amount = amount.quantize(Decimal("0.01"))
        return int(amount) if amount == amount.to_integral_value() else float(amount)
    except (InvalidOperation, ValueError, TypeError):
        return 0


def parse_date(value):
    """PocketBase/ISO timestamps; naive legacy PocketBase dates are UTC."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def iso_date(value):
    parsed = parse_date(value)
    return parsed.isoformat().replace("+00:00", "Z") if parsed else ""


def listing_date(obj):
    published = parse_date(obj.get("published_at"))
    if published:
        return published, "Опубликовано"
    created = parse_date(obj.get("createdAt") or obj.get("created"))
    return (created, "Добавлено") if created else (None, "")


def newest_key(obj):
    stamp, _ = listing_date(obj)
    return (-(stamp.timestamp() if stamp else float("-inf")), str(obj.get("id") or ""))


def newest_first(objects):
    return sorted(objects, key=newest_key)


def file_urls(record_id, raw, *, videos=False):
    """Encode PocketBase file segments; videos only accept PB mp4/webm files.

    Existing image URLs remain supported, with http(s) and credentials checked.
    User-supplied video URLs are intentionally not treated as PB file names.
    """
    values = raw if isinstance(raw, list) else [raw] if raw else []
    base = urlsplit(C.PB_URL)
    valid_base = base.scheme in {"https", "http"} and base.hostname and not base.username and not base.password and not base.query and not base.fragment
    record_id = str(record_id or "")
    collection = str(C.PB_COLLECTION)
    out = []
    for value in values:
        name = value.get("name") if isinstance(value, dict) else value
        if not isinstance(name, str) or not name or any(ord(ch) < 32 for ch in name):
            continue
        try:
            parsed = urlsplit(name)
        except ValueError:
            continue
        if parsed.scheme or parsed.netloc:
            if videos or parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
                continue
            url = name
        else:
            if not valid_base or not re.fullmatch(r"[A-Za-z0-9_-]+", record_id) or not re.fullmatch(r"[A-Za-z0-9_-]+", collection):
                continue
            if name in {".", ".."} or any(ch in name for ch in "/\\?#:"):
                continue
            if videos and name.rsplit(".", 1)[-1].casefold() not in {"mp4", "webm"}:
                continue
            url = f"{C.PB_URL}/api/files/{quote(collection, safe='')}/{quote(record_id, safe='')}/{quote(name, safe='')}"
        if url not in out:
            out.append(url)
        if videos and len(out) == 3:
            break
    return out
