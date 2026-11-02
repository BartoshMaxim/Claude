"""otomoto.pl — данные из встроенного JSON (__NEXT_DATA__), без парсинга вёрстки.

Caddy живёт в двух категориях:
  * /osobowe/volkswagen/caddy        — Kombi / Life / Style (M1 и N1 5-местные)
  * /dostawcze/volkswagen/q-caddy    — Cargo (в «dostawcze» нет фильтра модели, ищем по q)
Цена в поиске всегда brutto; при INVOICE_ISSUED есть Faktura VAT, netto берём из
netPrice (или brutto/1,23). На странице объявления — описание, места, VIN
(VIN otomoto отдаёт только зашифрованным за reCAPTCHA — не используем).
"""
from __future__ import annotations

import json
import logging
import math
import re
from urllib.parse import urlencode

from ..model import Listing, fill_net_gross
from ..textutil import detect_model_year, detect_seats, detect_version, html_to_text

log = logging.getLogger(__name__)
NAME = "otomoto"
BASE = "https://www.otomoto.pl"
PAGE_SIZE = 32


def _next_data(html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("нет __NEXT_DATA__")
    return json.loads(m.group(1))


def _search_payload(html: str) -> dict:
    d = _next_data(html)
    for v in d["props"]["pageProps"].get("urqlState", {}).values():
        x = json.loads(v["data"]) if isinstance(v.get("data"), str) else v.get("data")
        if isinstance(x, dict) and "advertSearch" in x:
            return x["advertSearch"]
    raise ValueError("нет advertSearch в __NEXT_DATA__")


def build_urls(cfg: dict) -> list[tuple[str, str]]:
    s = cfg["search"]
    params: list[tuple[str, str]] = [("search[order]", "created_at:desc")]
    if s.get("year_from"):
        params.append(("search[filter_float_year:from]", str(s["year_from"])))
    if s.get("year_to"):
        params.append(("search[filter_float_year:to]", str(s["year_to"])))
    if s.get("price_min"):
        params.append(("search[filter_float_price:from]", str(s["price_min"])))
    if s.get("price_max"):
        params.append(("search[filter_float_price:to]", str(s["price_max"])))
    for i, f in enumerate(s.get("fuel") or []):
        params.append((f"search[filter_enum_fuel_type][{i}]", f))
    for i, g in enumerate(s.get("gearbox") or []):
        params.append((f"search[filter_enum_gearbox][{i}]", g))
    if s.get("power_min"):
        params.append(("search[filter_float_engine_power:from]", str(s["power_min"])))
    if s.get("power_max"):
        params.append(("search[filter_float_engine_power:to]", str(s["power_max"])))
    if s.get("max_mileage") is not None:
        params.append(("search[filter_float_mileage:to]", str(s["max_mileage"])))
    if not s.get("include_used", True):
        params.append(("search[filter_enum_new_used]", "new"))
    q = urlencode(params)
    versions = {v.lower() for v in s.get("versions") or []}
    urls = []
    if not versions or versions & {"kombi", "maxi", "california"}:
        urls.append(("osobowe", f"{BASE}/osobowe/{s['make']}/{s['model']}?{q}"))
    if not versions or "cargo" in versions:
        urls.append(("dostawcze", f"{BASE}/dostawcze/{s['make']}/q-{s['model']}?{q}"))
    return urls


def _param(node: dict, key: str):
    for p in node.get("parameters") or []:
        if p.get("key") == key:
            return p.get("value")
    return None


def _int(v):
    try:
        return int(float(str(v).replace(" ", "")))
    except (TypeError, ValueError):
        return None


def _title(n: dict) -> str:
    t, sd = (n.get("title") or "").strip(), (n.get("shortDescription") or "").strip()
    if not sd or sd.lower() in t.lower():
        return t
    if t.lower() in sd.lower():
        return sd if sd.lower().startswith("volkswagen") else f"{t} {sd}"
    return f"{t} {sd}"


def parse_node(n: dict, category: str) -> Listing:
    price = n.get("price") or {}
    amount = float(price.get("amount", {}).get("value") or 0) or None
    badges = price.get("badges") or []
    invoice = "INVOICE_ISSUED" in badges or "INCLUDE_VAT" in badges
    seller_t = (n.get("seller") or {}).get("__typename", "")
    l = Listing(
        platform=NAME,
        source_id=str(n["id"]),
        url=n["url"],
        title=_title(n),
        price_listed=amount,
        price_gross=amount,
        price_net=float(price["netPrice"]["value"]) if price.get("netPrice") else None,
        price_basis="brutto" if price.get("isGross") else ("netto" if "INCLUDE_VAT" in badges else "brutto"),
        invoice_vat=invoice,
        year=_int(_param(n, "year")),
        mileage=_int(_param(n, "mileage")),
        engine_cc=_int(_param(n, "engine_capacity")),
        power_hp=_int(_param(n, "engine_power")),
        fuel=_param(n, "fuel_type"),
        gearbox=_param(n, "gearbox"),
        city=((n.get("location") or {}).get("city") or {}).get("name"),
        seller_type="dealer" if "Professional" in seller_t else ("private" if seller_t else None),
        seller_name=(n.get("sellerLink") or {}).get("name"),
        posted_at=n.get("createdAt"),
    )
    pd = n.get("priceDrop")
    if pd and pd.get("percentage"):
        l.price_drop_pct = float(pd["percentage"])
    hint = "dostawcze" if category == "dostawcze" else None
    l.version = detect_version(l.title, "", hint)
    if l.mileage is not None and l.mileage <= 100:
        l.condition = "new"
    fill_net_gross(l)
    return l


def apply_detail(l: Listing, html: str):
    ad = _next_data(html)["props"]["pageProps"].get("advert") or {}
    l.description = html_to_text(ad.get("description"))
    det = {d.get("key"): d.get("value") for d in ad.get("details") or []}
    l.seats = _int(det.get("nr_seats")) or detect_seats(l.description)
    nu = (det.get("new_used") or "").lower()
    if nu:
        l.condition = "new" if nu.startswith("now") else "used"
    pdict = ad.get("parametersDict") or {}
    vat = ((pdict.get("vat") or {}).get("values") or [{}])[0].get("value")
    if vat is not None:
        l.invoice_vat = str(vat) == "1"
    p = ad.get("advertPriceForPriceDrop") or {}
    if p.get("grossMinorAmount"):
        l.price_gross = p["grossMinorAmount"] / 100
        if p.get("netMinorAmount") and l.invoice_vat:
            l.price_net = p["netMinorAmount"] / 100
        l.price_basis = "netto" if p.get("isNet") else "brutto"
    seller = ad.get("seller") or {}
    if seller.get("type"):
        l.seller_type = "dealer" if seller["type"] == "PROFESSIONAL" else "private"
    l.seller_name = seller.get("name") or l.seller_name
    l.posted_at = ad.get("originalCreatedAt") or l.posted_at
    body = det.get("body_type")
    l.version = detect_version(l.title, l.description, body, l.seats)
    l.model_year = detect_model_year(l.description) or detect_model_year(l.title)
    m = re.search(r"wersj\w* wyposa\w*\s*:?\s*([A-Za-z]+)", l.description)
    if m:
        l.trim = m.group(1)
    l.detail_loaded = True
    fill_net_gross(l)


def fetch(client, cfg: dict, status: dict, prefilter) -> list[Listing]:
    pol = cfg["politeness"]
    search_age = pol["search_cache_hours"] * 3600
    detail_age = pol["detail_cache_days"] * 86400
    out: dict[str, Listing] = {}
    for category, url in build_urls(cfg):
        page, pages = 1, 1
        while page <= pages:
            u = url + (f"&page={page}" if page > 1 else "")
            r = client.get(u, max_age_s=search_age)
            a = _search_payload(r.text)
            total = a.get("totalCount") or 0
            pages = min(math.ceil(total / PAGE_SIZE), 15)
            for e in a.get("edges") or []:
                n = e["node"]
                if (n.get("title") or "").lower().find("caddy") < 0 and \
                        (n.get("shortDescription") or "").lower().find("caddy") < 0:
                    continue   # q=caddy в dostawcze иногда даёт Crafter/Transporter
                l = parse_node(n, category)
                out.setdefault(l.uid, l)
            status.setdefault("search_counts", {})[category] = total
            page += 1
    listings = [l for l in out.values() if prefilter(l)]
    # ID, отсеянные фильтром — чтобы их копии на OLX тоже отсеять (см. main)
    status["rejected_ids"] = [re.search(r"-(ID\w+)\.html", l.url).group(1)
                              for l in out.values() if not prefilter(l) and "-ID" in l.url]
    # детальные страницы: сначала те, что уже в кэше, потом лучшие по цене
    limit = pol["detail_pages_per_source"]
    listings.sort(key=lambda l: (client.cache_get(l.url, detail_age) is None, l.price_gross or 9e9))
    fetched = 0
    for l in listings:
        cached = client.cache_get(l.url, detail_age)
        if cached is None:
            if fetched >= limit:
                continue
            fetched += 1
        try:
            r = cached or client.get(l.url, max_age_s=detail_age)
            apply_detail(l, r.text)
        except Exception as e:  # noqa: BLE001
            if e.__class__.__name__ == "BudgetExceeded":
                status["note"] = (status.get("note", "") + " лимит страниц — часть деталей не загружена").strip()
                break
            log.warning("otomoto detail %s: %s", l.url, e)
    # после загрузки деталей версия/параметры могли уточниться — фильтруем ещё раз
    final = [l for l in listings if prefilter(l)]
    status["rejected_ids"] += [re.search(r"-(ID\w+)\.html", l.url).group(1)
                               for l in listings if l not in final and "-ID" in l.url]
    return final
