from __future__ import annotations

from dataclasses import dataclass, field, asdict

VAT = 1.23


@dataclass
class Listing:
    platform: str                 # otomoto | olx | vehis | carleasepolska | ayvens_flex
    source_id: str
    url: str
    title: str
    kind: str = "sale"            # sale | lease
    price_listed: float | None = None   # как показано на сайте
    price_net: float | None = None
    price_gross: float | None = None
    price_basis: str | None = None      # netto | brutto — как указал продавец
    invoice_vat: bool | None = None     # Faktura VAT 23%
    year: int | None = None
    model_year: int | None = None
    mileage: int | None = None
    engine_cc: int | None = None
    power_hp: int | None = None
    fuel: str | None = None
    gearbox: str | None = None
    version: str | None = None          # Kombi / Cargo / Kombi Maxi / Cargo Maxi / California
    trim: str | None = None
    seats: int | None = None
    city: str | None = None
    seller_type: str | None = None      # dealer | private | leasing
    seller_name: str | None = None
    posted_at: str | None = None
    condition: str | None = None        # new | used
    vin: str | None = None
    external_ref: str | None = None     # например, OLX -> URL otomoto
    description: str = ""
    monthly_rate_net: float | None = None
    lease_terms: str | None = None
    price_drop_pct: float | None = None  # из данных платформы
    # вычисляемые
    fleet_flag: bool = False
    fleet_phrases: list[str] = field(default_factory=list)
    real_price_net: float | None = None
    real_price_gross: float | None = None
    real_price_note: str | None = None
    detail_loaded: bool = False

    @property
    def uid(self) -> str:
        return f"{self.platform}:{self.source_id}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["uid"] = self.uid
        return d


def fill_net_gross(l: Listing):
    """brutto = netto × 1,23 (только если есть Faktura VAT 23%)."""
    if l.invoice_vat:
        if l.price_net is None and l.price_gross is not None:
            l.price_net = round(l.price_gross / VAT)
        if l.price_gross is None and l.price_net is not None:
            l.price_gross = round(l.price_net * VAT)
    else:
        if l.price_gross is None and l.price_listed is not None:
            l.price_gross = l.price_listed
