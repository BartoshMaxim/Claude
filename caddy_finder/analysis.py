"""Дедупликация, «реальная» цена для JDG и оценка совпадения с ориентиром."""
from __future__ import annotations

import re
from collections import defaultdict

from .model import Listing
from .textutil import analyse_conditions, has_facelift

PLATFORM_PRIORITY = {"otomoto": 0, "vehis": 1, "olx": 2}


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _otomoto_id(url: str | None) -> str | None:
    m = re.search(r"-(ID[0-9A-Za-z]+)\.html", url or "")
    return m.group(1) if m else None


def dedup(listings: list[Listing]) -> dict[str, list[str]]:
    """Возвращает {dedup_key: [uid,...]} и проставляет l.dedup_key.

    Порядок признаков: VIN → ссылка OLX→otomoto (external_url) →
    дилер + год + мощность + пробег(±50 км) + цена.
    """
    parent = {l.uid: l.uid for l in listings}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_vin, by_oto, by_fp = defaultdict(list), defaultdict(list), defaultdict(list)
    for l in listings:
        if l.kind == "lease":
            continue
        if l.vin:
            by_vin[l.vin].append(l.uid)
        oid = _otomoto_id(l.url) if l.platform == "otomoto" else _otomoto_id(l.external_ref)
        if oid:
            by_oto[oid].append(l.uid)
        price = round(l.price_gross or l.price_listed or 0)
        if price and l.year:
            fp = (l.year, l.power_hp, round((l.mileage or 0) / 50), price, l.city and _norm(l.city))
            by_fp[fp].append(l.uid)
    for group in list(by_vin.values()) + list(by_oto.values()):
        for u in group[1:]:
            union(group[0], u)
    # отпечаток склеивает только РАЗНЫЕ платформы: у дилера бывает несколько
    # одинаковых машин по одной цене — внутри одной платформы их не сливаем
    for group in by_fp.values():
        plat = {}
        for u in group:
            plat.setdefault(u.split(":", 1)[0], u)
        if len(plat) > 1:
            first = next(iter(plat.values()))
            for u in plat.values():
                union(first, u)
    clusters: dict[str, list[str]] = defaultdict(list)
    for l in listings:
        clusters[find(l.uid)].append(l.uid)
    return clusters


def merge_cluster(items: list[Listing]) -> Listing:
    """Основная запись — с otomoto (больше полей), дополняется VIN и т.п. из дублей."""
    items = sorted(items, key=lambda l: (PLATFORM_PRIORITY.get(l.platform, 9), not l.detail_loaded))
    main = items[0]
    for o in items[1:]:
        for f in ("vin", "seats", "model_year", "engine_cc", "power_hp", "seller_name",
                  "trim", "gearbox", "fuel"):
            if getattr(main, f) in (None, "") and getattr(o, f) not in (None, ""):
                setattr(main, f, getattr(o, f))
        if len(o.description) > len(main.description) and not main.detail_loaded:
            main.description = o.description
    return main


def cost_for_me(l: Listing, vat_status: str, deduct_pct: float = 100) -> tuple[float | None, str]:
    """Цена для сравнения: czynny → netto при FV 23%, иначе полная; zwolniony → brutto.
    deduct_pct < 100: к netto добавляется невычитаемая часть VAT."""
    net, gross = l.real_price_net, l.real_price_gross or l.price_listed
    if vat_status == "czynny":
        if l.invoice_vat and net:
            if deduct_pct >= 100:
                return net, "netto"
            return round(net + net * 0.23 * (1 - deduct_pct / 100)), f"netto + {100 - deduct_pct:.0f}% VAT"
        return gross, "brutto (без FV — VAT не вычесть)"
    return gross, "brutto"


def match_score(l: Listing, ref: dict) -> tuple[int, list[str]]:
    """0–100: насколько авто похоже на ориентир (1.5 TSI 116 KM, MY2027, 2755 mm)."""
    pts, why = 0, []
    text = f"{l.title}\n{l.description}"
    if l.engine_cc and abs(l.engine_cc - ref["engine_cc"]) <= 10 and (l.fuel or "").startswith(("petrol", "gas")):
        pts += 30; why.append("1.5 TSI")
    elif re.search(r"1[.,]5\s*TSI", text, re.I):
        pts += 25; why.append("1.5 TSI (из текста)")
    if l.power_hp == ref["power_hp"]:
        pts += 20; why.append(f"{ref['power_hp']} KM")
    elif l.power_hp and abs(l.power_hp - ref["power_hp"]) <= 10:
        pts += 8
    if l.model_year == ref["model_year"]:
        pts += 20; why.append(f"MY{ref['model_year']}")
    elif l.year == ref["model_year"] or (l.year and l.year >= ref["model_year"] - 1):
        pts += 10; why.append(f"rok {l.year}")
    if has_facelift(text):
        pts += 5; why.append("po lifcie")
    if l.version and "maxi" not in l.version.lower():
        pts += 10; why.append("2755 mm")
    if l.version and l.version.startswith("Kombi"):
        pts += 5
    if l.condition == "new" or (l.mileage is not None and l.mileage <= 100):
        pts += 5; why.append("nowy")
    target = ref["fleet_price_net"]
    if l.real_price_net:
        diff = (l.real_price_net - target) / target
        pts += max(0, int(5 - abs(diff) * 25))
    return min(pts, 100), why


def enrich(listings: list[Listing], cfg: dict):
    for l in listings:
        if l.kind == "sale":
            analyse_conditions(l)
        else:
            l.real_price_net, l.real_price_gross = l.price_net, l.price_gross
