"""Оферты najmu długoterminowego с опубликованной ставкой.

Проверено вручную (ноябрь 2026), что реально отдаёт Caddy с ценой:
  * carleasepolska.pl — брокер najmu: карточки «Volkswagen Caddy …», цена авто
    netto и ставка netto/мес. (страницы /wynajem-dlugoterminowy/ разрешены robots.txt)
  * ayvens.com/pl-pl — Ayvens Flex (najem średnioterminowy 1–24 мес.):
    страница модели Caddy со ставкой netto. В каталоге «oferta dla firm» Caddy нет.
Не нашёл Caddy: Ayvens «oferta dla firm», Otomoto Lease (бывш. Carsmile),
каталог Arval (sitemap wynajem-oferty), VWFS (robots.txt → 301, не исследован).
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from ..model import Listing, fill_net_gross

log = logging.getLogger(__name__)


def _pln(s: str) -> float | None:
    s = s.replace(" ", " ")
    m = re.search(r"(\d{1,3}(?:[ .]\d{3})+|\d+)(?:,(\d{1,2}))?", s)
    if not m:
        return None
    v = float(re.sub(r"[ .]", "", m.group(1)))
    if m.group(2):
        v += float("0." + m.group(2))
    return v


# ------------------------------------------------------------ Car Lease Polska
CLP_BASE = "https://carleasepolska.pl"
CLP_PAGES = [
    "/wynajem-dlugoterminowy/marki/6/volkswagen/modele/269/caddy",
    "/wynajem-dlugoterminowy/marki/6/volkswagen/modele/650/caddy-cargo",
]


def fetch_carleasepolska(client, cfg: dict, status: dict, prefilter) -> list[Listing]:
    age = cfg["politeness"]["search_cache_hours"] * 3600
    out: dict[str, Listing] = {}
    for path in CLP_PAGES:
        r = client.get(CLP_BASE + path, max_age_s=age)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[data-component=card-car]"):
            href = a.get("href", "")
            m = re.search(r"/(\d+)/samochod/", href)
            if not m:
                continue
            parts = list(a.stripped_strings)
            txt = " | ".join(parts)
            if "caddy" not in txt.lower():
                continue
            # «… | 158 671 zł | Diesel | 102 KM | Manual | cena netto | uwzgl. rabat i serwis | 1 798 | ,10 zł | 2 091 zł | -14%»
            prices = [i for i, p in enumerate(parts) if p.endswith("zł")]
            car_price = _pln(parts[prices[0]]) if prices else None
            rate = None
            if len(prices) >= 2:
                i = prices[1]
                rate = _pln(parts[i - 1] + parts[i]) if parts[i].startswith(",") else _pln(parts[i])
            name_parts = [p for p in parts[:prices[0]] if p not in ("od ręki", "Porównaj", "Ulubione")
                          and not re.match(r"^\d+/\d+$", p)] if prices else []
            power = next((int(re.sub(r"\D", "", p)) for p in parts if p.endswith(" KM")), None)
            fuel = next((p for p in parts if p in ("Diesel", "Benzyna", "Hybryda", "Elektryczny")), None)
            gear = next((p for p in parts if p in ("Manual", "Automat")), None)
            l = Listing(
                platform="carleasepolska", source_id=m.group(1), url=CLP_BASE + href,
                title=" ".join(name_parts) or "Volkswagen Caddy", kind="lease",
                price_listed=car_price, price_net=car_price, price_basis="netto", invoice_vat=True,
                power_hp=power,
                fuel={"Diesel": "diesel", "Benzyna": "petrol", "Hybryda": "hybrid"}.get(fuel, fuel),
                gearbox={"Manual": "manual", "Automat": "automatic"}.get(gear, gear),
                seller_type="leasing", seller_name="Car Lease Polska",
                monthly_rate_net=rate, condition="new",
                lease_terms="najem długoterminowy; ставка «od», netto/мес., uwzgl. rabat i serwis",
            )
            l.version = ("Cargo" if "cargo" in path else "Kombi") + (" Maxi" if "maxi" in l.title.lower() else "")
            fill_net_gross(l)
            out.setdefault(l.uid, l)
    status["search_counts"] = {"caddy": len(out)}
    return list(out.values())


# ------------------------------------------------------------ Ayvens Flex
AYV_BASE = "https://www.ayvens.com"
AYV_PAGE = "/pl-pl/wynajem-elastyczny-ayvens-flex/volkswagen/caddy/"


def fetch_ayvens_flex(client, cfg: dict, status: dict, prefilter) -> list[Listing]:
    age = cfg["politeness"]["search_cache_hours"] * 3600
    r = client.get(AYV_BASE + AYV_PAGE, max_age_s=age)
    soup = BeautifulSoup(r.text, "html.parser")
    out: dict[str, Listing] = {}
    for a in soup.find_all("a", href=re.compile(r"/wynajem-elastyczny-ayvens-flex/oferta/\d+/")):
        href = a["href"]
        oid = re.search(r"/oferta/(\d+)/", href).group(1)
        if f"ayvens_flex:{oid}" in out:
            continue
        card = a
        for _ in range(6):
            if "zł" in card.get_text() and "caddy" in card.get_text().lower():
                break
            card = card.parent
        parts = list(card.stripped_strings)
        txt = " | ".join(parts)
        if "caddy" not in txt.lower():
            continue
        rate_s = next((p for p in parts if p.endswith("zł")), None)
        idx = next((i for i, p in enumerate(parts) if "caddy" in p.lower()), 0)
        version = parts[idx + 1] if idx + 1 < len(parts) else ""
        pm = re.search(r"(\d{2,3})\s*km", version, re.I)
        l = Listing(
            platform="ayvens_flex", source_id=oid,
            url=href if href.startswith("http") else AYV_BASE + href,
            title=f"Volkswagen Caddy {version}".strip(), kind="lease",
            monthly_rate_net=_pln(rate_s.replace(".", " ")) if rate_s else None,
            power_hp=int(pm.group(1)) if pm else None,
            fuel="diesel" if "tdi" in version.lower() else ("petrol" if "tsi" in version.lower() else None),
            gearbox="manual" if re.search(r"\bman", version, re.I) else ("automatic" if "dsg" in version.lower() else None),
            seller_type="leasing", seller_name="Ayvens (Flex)", invoice_vat=True, condition="new",
            lease_terms="Ayvens Flex — najem 1–24 мес., " + ", ".join(p for p in parts if "wpłaty" in p),
            version="Kombi",
        )
        out[l.uid] = l
    status["search_counts"] = {"caddy": len(out)}
    return list(out.values())
