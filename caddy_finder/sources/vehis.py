"""vehis.pl — онлайн-лизинг с собственной витриной авто (новые и б/у).

Данные — встроенный JSON Nuxt (__NUXT_DATA__, формат devalue). У каждого авто
есть цена дилера (без условий) и «cena w VEHIS» — ниже, но только при
финансировании через VEHIS. Поэтому объявление получает флаг «финансирование»,
а реальной ценой считается цена дилера.
"""
from __future__ import annotations

import json
import logging
import re

from ..model import Listing, fill_net_gross

log = logging.getLogger(__name__)
NAME = "vehis"
BASE = "https://vehis.pl"
PAGES = [
    ("Kombi", "/osobowe/volkswagen/caddy-osobowy"),
    ("Kombi", "/osobowe/volkswagen/caddy"),
    ("Cargo", "/dostawcze/volkswagen/caddy/furgon"),
    ("Cargo", "/dostawcze/volkswagen/caddy-osobowy/furgon"),
]
FUEL = {"gas": "petrol", "diesel": "diesel", "hybrid": "hybrid", "electric": "electric"}


def nuxt_payload(html: str):
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("нет __NUXT_DATA__")
    arr = json.loads(m.group(1))
    memo: dict[int, object] = {}
    wrappers = {"Reactive", "ShallowReactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef", "NuxtError"}

    def r(i):
        if i in memo:
            return memo[i]
        v = arr[i]
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in wrappers | {"Set", "Map", "Date"}:
                if v[0] == "Date":
                    return v[1]
                if v[0] == "Set":
                    return [r(x) for x in v[1:]]
                if v[0] == "Map":
                    return {str(r(v[k])): r(v[k + 1]) for k in range(1, len(v), 2)}
                return r(v[1]) if len(v) > 1 else None
            out: list = []
            memo[i] = out
            out.extend(r(x) if isinstance(x, int) else x for x in v)
            return out
        if isinstance(v, dict):
            out_d: dict = {}
            memo[i] = out_d
            for k, x in v.items():
                out_d[k] = r(x) if isinstance(x, int) else x
            return out_d
        return v

    return r(0)


def _money(p: dict | None, key: str):
    v = (p or {}).get(key)
    return v / 100 if isinstance(v, (int, float)) else None


def parse_item(it: dict, version_hint: str, html: str) -> Listing:
    uuid = it["uuid"]
    m = re.search(r'href="(/wyszukaj/oferta/[^"]*' + re.escape(uuid) + ')"', html)
    url = BASE + (m.group(1) if m else f"/wyszukaj/oferta/volkswagen/caddy/{uuid}")
    dealer_net = _money(it.get("price"), "priceNet")
    vehis_net = _money(it.get("discountPrice"), "priceNet")
    catalog_net = _money(it.get("originalPrice"), "priceNet")
    variant = it.get("variant") or ""
    l = Listing(
        platform=NAME, source_id=uuid, url=url,
        title=f"Volkswagen {variant} {it.get('engineCapacityShortcut') or ''} "
              f"{(it.get('enginePower') or {}).get('value') or ''} KM {it.get('transmissionShortcut') or ''}".strip(),
        price_listed=_money(it.get("discountPrice"), "priceGross") or _money(it.get("price"), "priceGross"),
        price_net=vehis_net or dealer_net,
        price_gross=_money(it.get("discountPrice"), "priceGross") or _money(it.get("price"), "priceGross"),
        price_basis="netto",
        invoice_vat=True,
        year=it.get("productionYear"),
        mileage=it.get("mileage"),
        engine_cc=it.get("engineCapacity"),
        power_hp=(it.get("enginePower") or {}).get("value"),
        fuel=FUEL.get(it.get("fuelType"), it.get("fuelType")),
        gearbox="manual" if it.get("transmission") == "manual" else "automatic",
        city=(it.get("location") or {}).get("city"),
        seller_type="leasing",
        seller_name="VEHIS" if it.get("ownership") == "vehis" else "partner VEHIS",
        posted_at=it.get("publishedAt"),
        condition="new" if it.get("type") == "new" else "used",
        trim=variant.replace("Caddy", "").replace("1.5 TSI", "").replace("2.0 TDI", "").strip() or None,
    )
    body = (it.get("bodyType") or "").lower()
    base = "Cargo" if ("furgon" in body or version_hint == "Cargo" and "kombi" not in body) else "Kombi"
    l.version = base + (" Maxi" if "maxi" in variant.lower() else "")
    if "california" in variant.lower():
        l.version = "California"
    # синтетическое описание из структурированных цен — его же разбирает общий анализатор
    parts = []
    if vehis_net and dealer_net and vehis_net < dealer_net:
        parts.append(f"Cena w VEHIS z finansowaniem VEHIS: {vehis_net:.0f} zł netto.")
    if dealer_net:
        parts.append(f"Cena dealera bez finansowania VEHIS: {dealer_net:.0f} zł netto.")
    if catalog_net:
        parts.append(f"Cena katalogowa: {catalog_net:.0f} zł netto.")
    l.description = "\n".join(parts)
    l.detail_loaded = True
    fill_net_gross(l)
    return l


def fetch(client, cfg: dict, status: dict, prefilter) -> list[Listing]:
    age = cfg["politeness"]["search_cache_hours"] * 3600
    out: dict[str, Listing] = {}
    counts = {}
    for hint, path in PAGES:
        r = client.get(BASE + path, max_age_s=age)
        data = (nuxt_payload(r.text) or {}).get("data") or {}
        for key, block in data.items():
            if not key.startswith("search-results") or not isinstance(block, dict):
                continue
            items = block.get("items") or []
            counts[path] = (block.get("meta") or {}).get("totalItems", len(items))
            if (block.get("meta") or {}).get("nextCursor"):
                status["note"] = "есть следующая страница — загружена только первая (20 шт.)"
            for it in items:
                if "caddy" not in (it.get("model") or "").lower():
                    continue
                l = parse_item(it, hint, r.text)
                out.setdefault(l.uid, l)
    status["search_counts"] = counts
    return [l for l in out.values() if prefilter(l)]
