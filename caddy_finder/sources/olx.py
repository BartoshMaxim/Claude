"""olx.pl — публичный JSON API /api/v1/offers/ (явно разрешён в robots.txt:
«Allow: /api/v1/offers/»).

HTML-поиск OLX отдаёт «Human Verification» (капча) — его не трогаем.
API отвечает только «настоящему» браузеру (requests получает 403 от CloudFront),
поэтому ходим через Playwright, без логина и без решения капчи.

Почти все объявления Caddy на OLX — экспорт из otomoto (partner=otomoto_pl_form,
поле external_url указывает на otomoto) — используется для дедупликации. Зато
OLX отдаёт VIN открытым текстом.
"""
from __future__ import annotations

import logging
from urllib.parse import urlencode

from ..model import Listing, fill_net_gross
from ..textutil import detect_model_year, detect_seats, detect_version, html_to_text

log = logging.getLogger(__name__)
NAME = "olx"
API = "https://www.olx.pl/api/v1/offers/"
CAT_OSOBOWE = 84
LIMIT = 40

FUEL_MAP = {"petrol": "petrol", "diesel": "diesel", "hybrid": "hybrid", "lpg": "lpg",
            "cng": "cng", "electric": "electric"}


def _params(o: dict) -> dict:
    return {p["key"]: p.get("value") or {} for p in o.get("params") or []}


def _int(v):
    try:
        return int(float(str(v).replace(" ", "")))
    except (TypeError, ValueError):
        return None


def parse_offer(o: dict) -> Listing:
    p = _params(o)
    price = p.get("price") or {}
    desc = html_to_text(o.get("description"))
    title = o.get("title") or ""
    text = f"{title}\n{desc}".lower()
    invoice = "faktura vat" in text or "fv23" in text or "fv 23" in text or "netto" in text
    if "vat marża" in text or "vat marza" in text:
        invoice = False
    vin = ((p.get("vin") or {}).get("key") or "").strip().upper() or None
    if vin and (len(vin) != 17 or set(vin[3:]) <= {"0"}):
        vin = None   # заглушки вида WVW00000000000000
    l = Listing(
        platform=NAME,
        source_id=str(o["id"]),
        url=o["url"],
        title=title,
        price_listed=float(price["value"]) if price.get("value") else None,
        price_basis="brutto",
        invoice_vat=invoice if o.get("business") else False,
        year=_int((p.get("year") or {}).get("key")),
        mileage=_int((p.get("milage") or {}).get("key")),
        engine_cc=_int((p.get("enginesize") or {}).get("key")),
        power_hp=_int((p.get("enginepower") or {}).get("key")),
        fuel=(p.get("petrol") or {}).get("key"),
        gearbox=(p.get("transmission") or {}).get("key"),
        city=((o.get("location") or {}).get("city") or {}).get("name"),
        seller_type="dealer" if o.get("business") else "private",
        seller_name=(o.get("user") or {}).get("company_name") or None,
        posted_at=o.get("created_time"),
        vin=vin,
        external_ref=o.get("external_url"),
        description=desc,
        detail_loaded=True,
    )
    l.price_gross = l.price_listed
    l.seats = detect_seats(desc)
    l.version = detect_version(title, desc, (p.get("car_body") or {}).get("label"), l.seats)
    l.model_year = detect_model_year(desc) or detect_model_year(title)
    if l.mileage is not None and l.mileage <= 100:
        l.condition = "new"
    fill_net_gross(l)
    return l


def _query(cfg: dict, osobowe: bool) -> list[tuple[str, str]]:
    s = cfg["search"]
    q: list[tuple[str, str]] = [("limit", str(LIMIT))]
    if osobowe:
        q += [("category_id", str(CAT_OSOBOWE)), ("filter_enum_model[0]", s["model"])]
        if s.get("year_from"):
            q.append(("filter_float_year:from", str(s["year_from"])))
        if s.get("year_to"):
            q.append(("filter_float_year:to", str(s["year_to"])))
        if s.get("price_min"):
            q.append(("filter_float_price:from", str(s["price_min"])))
        if s.get("price_max"):
            q.append(("filter_float_price:to", str(s["price_max"])))
        for i, f in enumerate(s.get("fuel") or []):
            q.append((f"filter_enum_petrol[{i}]", FUEL_MAP.get(f, f)))
        for i, g in enumerate(s.get("gearbox") or []):
            q.append((f"filter_enum_transmission[{i}]", g))
        if s.get("max_mileage") is not None:
            q.append(("filter_float_milage:to", str(s["max_mileage"])))
    else:
        q += [("query", f"{s['make']} {s['model']}"), ("sort_by", "created_at:desc")]
    return q


def fetch(client, cfg: dict, status: dict, prefilter) -> list[Listing]:
    age = cfg["politeness"]["search_cache_hours"] * 3600
    versions = {v.lower() for v in cfg["search"].get("versions") or []}
    runs = [(True, 15)]
    if not versions or "cargo" in versions:
        runs.append((False, 3))     # dostawcze: поиск по тексту, первые 3 страницы
    out: dict[str, Listing] = {}
    for osobowe, max_pages in runs:
        base = _query(cfg, osobowe)
        for page in range(max_pages):
            url = API + "?" + urlencode([("offset", str(page * LIMIT))] + base)
            d = client.get(url, max_age_s=age, browser=True).json()
            data = d.get("data") or []
            for o in data:
                if not osobowe and (o.get("category") or {}).get("id") == 207:
                    continue          # osobowe уже взяли первым запросом
                if "caddy" not in (o.get("title") or "").lower():
                    continue
                try:
                    l = parse_offer(o)
                except Exception as e:  # noqa: BLE001
                    log.warning("olx parse %s: %s", o.get("id"), e)
                    continue
                if l.year is None or (l.price_listed or 0) < 15000:
                    continue          # запчасти/аксессуары «do Caddy»
                out.setdefault(l.uid, l)
            total = (d.get("metadata") or {}).get("total_elements") or 0
            status.setdefault("search_counts", {})["osobowe" if osobowe else "tekst"] = total
            if not (d.get("links") or {}).get("next") or (page + 1) * LIMIT >= total:
                break
    return [l for l in out.values() if prefilter(l)]
