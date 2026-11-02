from __future__ import annotations

from pathlib import Path

import yaml

from .model import Listing


def load(path: str | Path = "config.yaml") -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    vs = cfg["company"]["vat_status"]
    if vs not in ("czynny", "zwolniony"):
        raise ValueError("company.vat_status должен быть czynny или zwolniony")
    return cfg


FUEL_ALIASES = {
    "petrol": {"petrol", "benzyna", "gas"},
    "diesel": {"diesel"},
    "hybrid": {"hybrid", "plugin-hybrid", "hybryda"},
    "cng": {"cng", "petrol-cng"},
    "lpg": {"lpg", "petrol-lpg"},
    "electric": {"electric", "elektryczny"},
}


def make_prefilter(cfg: dict):
    """Фильтр по параметрам конфига. Неизвестные (None) значения пропускаем."""
    s = cfg["search"]
    fuels = set()
    for f in s.get("fuel") or []:
        fuels |= FUEL_ALIASES.get(f, {f})
    gears = {g.lower() for g in s.get("gearbox") or []}
    versions = {v.lower() for v in s.get("versions") or []}

    def ok(l: Listing) -> bool:
        if l.kind == "lease":
            return True
        if l.year is None or (l.price_listed or 0) < 15000:
            return False              # не авто (запчасти) или нет базовых данных
        if l.year is not None:
            if s.get("year_from") and l.year < s["year_from"]:
                return False
            if s.get("year_to") and l.year > s["year_to"]:
                return False
        p = l.price_gross or l.price_listed
        if p is not None:
            if s.get("price_min") and p < s["price_min"]:
                return False
            if s.get("price_max") and p > s["price_max"]:
                return False
        if fuels and l.fuel and l.fuel.lower() not in fuels:
            return False
        if gears and l.gearbox and l.gearbox.lower() not in gears:
            return False
        if l.power_hp is not None:
            if s.get("power_min") and l.power_hp < s["power_min"]:
                return False
            if s.get("power_max") and l.power_hp > s["power_max"]:
                return False
        if s.get("max_mileage") is not None and l.mileage is not None and l.mileage > s["max_mileage"]:
            return False
        if not s.get("include_used", True) and l.condition == "used":
            return False
        if versions and l.version:
            parts = l.version.lower().split()
            if parts[0] not in versions:
                return False
            if "maxi" in parts and "maxi" not in versions:
                return False
        return True

    return ok
