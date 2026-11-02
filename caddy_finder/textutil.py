"""Анализ текста объявлений: флотовые/финансовые условия, «реальная» цена,
рок модельный, версия кузова."""
from __future__ import annotations

import html as htmllib
import re

from bs4 import BeautifulSoup

from .model import VAT, Listing

# Фразы, указывающие, что цена в объявлении — условная (флота, финансирование,
# лизинг, кредит). Каждая найденная фраза показывается в отчёте.
FLEET_PATTERNS = [
    r"cen\w* dla firm\w* posiadaj\w* flot\w*",
    r"posiadaj\w* flot\w*",
    r"(?<!zapytaj o )(?<!zapytaj o specjalne )rabat\w* flotow\w*",
    r"program\w* flotow\w*",
    r"warunk\w* flotow\w*",
    r"cen\w* flotow\w*",
    r"(?:cen\w*|sprzeda\w*) dla klient\w* flotow\w*",
    r"small fleet",
    r"ofert\w* skierowan\w* (?:jest )?(?:wy\w*cznie |tylko )?do (?:przedsi\w*biorc\w*|klient\w* firmow\w*)",
    r"cen\w* (?:w|przy) leasingu",
    r"cen\w* leasingow\w*",
    r"cen\w* z finansowaniem",
    r"cen\w* (?:w|przy) kredycie",
    r"(?:cen\w*|zakup\w*) przy finansowaniu",
    r"przy finansowaniu (?:przez |w )?(?:vwfs|volkswagen financial|vw bank|vw leasing)",
    r"przy zakupie (?:w|z) (?:leasing|kredyt|finansowan)\w*",
    r"cena obowi\w*zuje (?:przy|wy\w*cznie|tylko) (?:finansowan|leasing|kredyt|zakup\w* (?:w|z) (?:leasing|kredyt|finans))\w*",
    r"cena dotyczy (?:finansowania|leasingu|klient\w* flotow)\w*",
    r"warunk\w* (?:otrzymania|uzyskania) (?:ceny|rabatu)",
    r"bez (?:promocyjnego )?finansowania",
    r"cen\w* uwarunkowan\w*",
    r"uwarunkowan\w* (?:zakupem|finansowaniem|leasingiem|posiadaniem)",
    r"cen\w* ko\w*cow\w* zale\w*n\w* od (?:formy )?finansowania",
    r"cena w vehis",
]
FLEET_RX = [re.compile(p, re.I) for p in FLEET_PATTERNS]

# Предложение с ценой, которая дана БЕЗ условий (то, что нужно JDG без флоты).
UNCONDITIONAL_RX = re.compile(
    r"bez (?:promocyjnego |obowi\w*zkowego )?(?:finansowania|leasingu|kredytu|floty|warunk\w*)"
    r"|bez koniecznosci (?:finansowania|posiadania floty)"
    r"|bez konieczno\w+ (?:finansowania|posiadania floty)"
    r"|cen\w* (?:regularn\w*|standardow\w*|katalogow\w* po rabacie|got\w*wkow\w*|bez rabatu flotowego)"
    r"|za got\w*wk\w*|zakup\w* got\w*wkow\w*"
    r"|dla (?:firm|klient\w*) (?:nie ?posiadaj\w*|bez) flot\w*",
    re.I,
)

PRICE_RX = re.compile(
    r"(?<![\d,.])(\d{1,3}(?:[  .]\d{3})+|\d{5,6})(?:,\d{1,2})?\s*(?:zł|pln|zl)\b\.?\s*(netto|brutto|net|gross)?",
    re.I,
)

MODEL_YEAR_RX = re.compile(
    r"(?:rok(?:u|iem)? modelow\w*|rocznik\w* modelow\w*|model year|\bMY|\br\.\s?m\.)\s*[:\-]?\s*(20\d{2}|\d{2})\b",
    re.I,
)
FACELIFT_RX = re.compile(r"po lift\w*|facelift\w*|\bFL\b|liftingow\w*|po face", re.I)


def html_to_text(s: str | None) -> str:
    if not s:
        return ""
    if "<" in s:
        s = BeautifulSoup(s, "html.parser").get_text("\n")
    s = htmllib.unescape(s)
    s = re.sub(r"[ \t ]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def _num(s: str) -> float:
    return float(re.sub(r"[  .]", "", s))


def find_prices(text: str) -> list[tuple[float, str | None, str]]:
    """[(значение, 'netto'|'brutto'|None, предложение)]"""
    out = []
    for sent in re.split(r"[\n;]|(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ])", text):
        for m in PRICE_RX.finditer(sent):
            val = _num(m.group(1))
            if not (20000 <= val <= 600000):
                continue
            basis = (m.group(2) or "").lower() or None
            if basis == "net":
                basis = "netto"
            if basis == "gross":
                basis = "brutto"
            if basis is None:
                tail = sent[m.end(): m.end() + 25].lower()
                head = sent[max(0, m.start() - 25): m.start()].lower()
                if "netto" in tail or "netto" in head:
                    basis = "netto"
                elif "brutto" in tail or "brutto" in head:
                    basis = "brutto"
            out.append((val, basis, sent.strip()))
    return out


def detect_fleet(text: str) -> list[str]:
    found = []
    for rx in FLEET_RX:
        for m in rx.finditer(text):
            ph = m.group(0).strip()
            if ph.lower() not in (f.lower() for f in found):
                found.append(ph)
    return found


def analyse_conditions(l: Listing):
    """Ставит fleet_flag и пытается вытащить цену без флоты/финансирования."""
    text = "\n".join(filter(None, [l.title, l.description]))
    phrases = detect_fleet(text)
    l.fleet_phrases = phrases
    l.fleet_flag = bool(phrases)

    l.real_price_net, l.real_price_gross, l.real_price_note = l.price_net, l.price_gross, None
    if not l.fleet_flag:
        return
    # ищем цену в предложении «bez finansowania / za gotówkę / dla firm bez floty»
    cands = [(v, b, s) for v, b, s in find_prices(text) if UNCONDITIONAL_RX.search(s)]
    if cands:
        v, basis, sent = cands[0]
        basis = basis or l.price_basis or "brutto"
        if basis == "netto":
            net, gross = v, round(v * VAT)
        else:
            gross, net = v, (round(v / VAT) if l.invoice_vat is not False else None)
        l.real_price_net, l.real_price_gross = net, gross
        l.real_price_note = f"цена без условий из описания: «{sent[:160]}»"
    else:
        l.real_price_note = ("цена может требовать флоты/финансирования — цену без условий "
                             "в описании не нашёл, уточнить у продавца")
        cat = [(v, b) for v, b, s in find_prices(text) if re.search(r"katalogow", s, re.I)]
        if cat:
            v, b = cat[0]
            l.real_price_note += f". Cena katalogowa (потолок, без рабатов): {v:,.0f} zł {b or ''}".replace(",", " ")


def detect_model_year(text: str) -> int | None:
    for m in MODEL_YEAR_RX.finditer(text):
        y = m.group(1)
        y = int(y) if len(y) == 4 else 2000 + int(y)
        if 2019 <= y <= 2030:
            return y
    return None


def has_facelift(text: str) -> bool:
    return bool(FACELIFT_RX.search(text))


def detect_version(title: str, desc: str, body_hint: str | None = None,
                   seats: int | None = None) -> str:
    t = f"{title} {body_hint or ''}".lower()
    d = desc.lower()
    if "california" in t:
        return "California"
    maxi = "maxi" in t or bool(re.search(r"rozstaw\w* osi\D{0,15}2\s?970", d)) or "maxi" in d[:300]
    cargo = bool(re.search(r"cargo|furgon|\bvan\b|dostawcz", t)) or (seats is not None and seats <= 2)
    if re.search(r"kombi|osobow|life|style|panamericana|\bm1\b", t):
        cargo = cargo and ("cargo" in t or "furgon" in t)
    base = "Cargo" if cargo else "Kombi"
    return f"{base} Maxi" if maxi else base


def detect_seats(text: str) -> int | None:
    m = re.search(r"\b([2-7])[ -]?(?:osobow|miejsc)", text, re.I)
    return int(m.group(1)) if m else None


def engine_label(cc: int | None, fuel: str | None) -> str:
    if not cc:
        return ""
    lit = f"{round(cc / 1000, 1):.1f}"
    f = (fuel or "").lower()
    if "diesel" in f:
        return f"{lit} TDI"
    if "hybr" in f:
        return f"{lit} eHybrid"
    if "petrol" in f or "benz" in f or f == "gas":
        return f"{lit} TSI"
    if "cng" in f:
        return f"{lit} TGI"
    return lit
