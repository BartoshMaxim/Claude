"""Точка входа: python -m caddy_finder [--config config.yaml] [--sources otomoto,olx] [--offline]"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path

from . import config as cfgmod
from .analysis import cost_for_me, dedup, enrich, match_score, merge_cluster
from .db import DB, now
from .http import Blocked, BudgetExceeded, Disallowed, PoliteClient
from .model import Listing
from .report import write_report
from .sources import autoplac, leasing, olx, otomoto, vehis
from .textutil import engine_label

log = logging.getLogger("caddy_finder")

SOURCES = {
    "otomoto": otomoto.fetch,
    "olx": olx.fetch,
    "autoplac": autoplac.fetch,
    "vehis": vehis.fetch,
    "carleasepolska": leasing.fetch_carleasepolska,
    "ayvens_flex": leasing.fetch_ayvens_flex,
}

CSV_COLS = ["platform", "url", "title", "price_listed", "price_net", "price_gross", "invoice_vat",
            "real_price_net", "real_price_gross", "cost_for_me", "cost_basis", "fleet_flag", "fleet_phrases",
            "real_price_note", "year", "model_year", "mileage", "engine", "power_hp", "gearbox", "version",
            "trim", "seats", "city", "seller_type", "seller_name", "posted_at", "vin", "first_seen",
            "price_history", "duplicates", "match_score", "monthly_rate_net", "kind"]


def fmt(v) -> str:
    return "—" if v is None else f"{v:,.0f}".replace(",", " ")


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Поиск VW Caddy на польских площадках")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--sources", help="через запятую, по умолчанию — все включённые в конфиге")
    ap.add_argument("--offline", action="store_true", help="только кэш, без сетевых запросов")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    cfg = cfgmod.load(args.config)
    if args.offline:
        cfg["politeness"]["max_pages"] = 0
        cfg["politeness"]["search_cache_hours"] = 24 * 365
    vat_status = cfg["company"]["vat_status"]
    prefilter = cfgmod.make_prefilter(cfg)
    wanted = args.sources.split(",") if args.sources else [k for k, v in cfg["sources"].items() if v]

    client = PoliteClient(cfg)
    db = DB(cfg["paths"]["db"])
    run_id = db.start_run()
    prev_run = db.previous_run_time(run_id)
    ts = now()
    t0 = time.time()

    all_listings: list[Listing] = []
    statuses: dict[str, dict] = {}
    try:
        for name in wanted:
            fn = SOURCES.get(name)
            if not fn:
                log.warning("неизвестный источник %s", name)
                continue
            st: dict = {}
            try:
                found = fn(client, cfg, st, prefilter)
                st["status"] = "ok"
                all_listings += found
                st["found"] = len(found)
            except Blocked as e:
                st.update(status="blocked", note=str(e), found=0)
            except Disallowed as e:
                st.update(status="robots", note=str(e), found=0)
            except BudgetExceeded as e:
                st.update(status="partial", note=str(e), found=0)
            except Exception as e:  # noqa: BLE001
                log.exception("источник %s упал", name)
                st.update(status="error", note=f"{type(e).__name__}: {e}", found=0)
            statuses[name] = st
            log.info("%s: %s, найдено %s %s", name, st["status"], st.get("found", 0), st.get("note", ""))
    finally:
        client.close()

    # копии на OLX объявлений otomoto, которые otomoto-фильтр уже отсеял
    rejected = set(statuses.get("otomoto", {}).pop("rejected_ids", []) or [])
    all_listings = [l for l in all_listings
                    if not (l.external_ref and any(f"-{i}.html" in l.external_ref for i in rejected))]
    for st in statuses.values():
        st.pop("rejected_ids", None)

    # ---------------------------------------------------------- анализ
    enrich(all_listings, cfg)
    by_uid = {l.uid: l for l in all_listings}
    clusters = dedup(all_listings)
    canon: list[Listing] = []
    dup_of: dict[str, list[str]] = {}
    for root, uids in clusters.items():
        items = [by_uid[u] for u in uids]
        main = merge_cluster(items) if len(items) > 1 else items[0]
        if len(items) > 1:
            enrich([main], cfg)        # описание могло дополниться
        canon.append(main)
        dup_of[main.uid] = [by_uid[u].url for u in uids if u != main.uid]

    ref = cfg["reference"]
    changes = {"new": [], "price_down": [], "price_up": [], "gone": []}
    rows = []
    for l in all_listings:
        is_main = l.uid in dup_of
        cost, basis = cost_for_me(l, vat_status, cfg['company'].get('vat_deduction_pct', 100))
        score, why = match_score(l, ref)
        extra = {"dedup_key": l.uid if is_main else next((m for m, d in dup_of.items() if l.url in d), l.uid),
                 "duplicates": json.dumps(dup_of.get(l.uid, []), ensure_ascii=False),
                 "match_score": score, "match_why": ", ".join(why), "cost_for_me": cost, "cost_basis": basis}
        res = db.upsert(l, ts, extra)
        if not is_main:
            continue
        hist = db.history(l.uid)
        row = l.to_dict()
        row.update(extra, engine=engine_label(l.engine_cc, l.fuel), price_history=hist,
                   duplicates=dup_of.get(l.uid, []), match_why=why)
        first = db.get(l.uid)["first_seen"]
        row["first_seen"] = first
        row["is_new"] = bool(prev_run) and first >= ts
        prices = [p for _, p in hist if p]
        row["price_dropped"] = (len(prices) > 1 and prices[-1] < max(prices[:-1])) or bool(l.price_drop_pct)
        if res["new"] and prev_run:
            changes["new"].append(row)
        elif res["old_price"] and l.price_listed and res["old_price"] != l.price_listed:
            row["old_price"] = res["old_price"]
            changes["price_down" if l.price_listed < res["old_price"] else "price_up"].append(row)
        rows.append(row)
    ok_platforms = [n for n, s in statuses.items() if s["status"] == "ok"]
    gone = db.mark_inactive(ok_platforms, ts)
    changes["gone"] = [dict(g) for g in gone if g["dedup_key"] == g["uid"]]
    db.commit()

    sale = [r for r in rows if r["kind"] == "sale"]
    lease = [r for r in rows if r["kind"] == "lease"]
    sale.sort(key=lambda r: (r["cost_for_me"] is None, r["cost_for_me"] or 0))
    top_match = sorted(sale, key=lambda r: (-r["match_score"], r["cost_for_me"] or 9e9))[:10]

    out_dir = Path(cfg["paths"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"generated": ts, "vat_status": vat_status, "reference": ref, "statuses": statuses,
            "pages_fetched": client.pages_fetched, "search": cfg["search"],
            "changes": {k: len(v) for k, v in changes.items()}, "prev_run": prev_run}
    write_report(out_dir / "report.html", sale, lease, top_match, meta)
    with open(out_dir / "listings.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore", delimiter=";")
        w.writeheader()
        for r in sale + lease:
            r2 = dict(r)
            r2["fleet_phrases"] = " | ".join(r["fleet_phrases"])
            r2["price_history"] = " ; ".join(f"{d[:10]}={p:.0f}" for d, p in r["price_history"] if p)
            r2["duplicates"] = " ".join(r["duplicates"])
            w.writerow(r2)

    summary = {"found_sale": len(sale), "found_lease": len(lease), "raw": len(all_listings),
               "statuses": {k: v["status"] for k, v in statuses.items()}, "changes": meta["changes"]}
    db.finish_run(run_id, client.pages_fetched, summary)
    print_summary(sale, lease, top_match, statuses, changes, meta, time.time() - t0, out_dir)
    return 0


def print_summary(sale, lease, top, statuses, changes, meta, secs, out_dir):
    unit = "netto" if meta["vat_status"] == "czynny" else "brutto"
    p = print
    p("\n" + "=" * 78)
    p(f"VW Caddy — сводка  ({meta['generated']}, {meta['pages_fetched']} сетевых запросов, {secs:.0f} с)")
    p("=" * 78)
    for name, st in statuses.items():
        p(f"  {name:15s} {st['status']:8s} найдено: {st.get('found', 0):3d}  {st.get('note', '')}")
    p(f"\nОбъявлений о продаже (после дедупликации): {len(sale)}   лизинг/najem: {len(lease)}")
    p(f"Сравнение по: {unit} (VAT {meta['vat_status']}); ориентир {fmt(meta['reference']['fleet_price_net'])} netto (флот)")
    p("\nЛучшие 5 по реальной цене:")
    for r in sale[:5]:
        flag = " [ФЛОТ/финансирование]" if r["fleet_flag"] else ""
        p(f"  {fmt(r['cost_for_me']):>9s} {r['cost_basis'][:6]:6s} | {r['year'] or '?'} {r['engine']} "
          f"{r['power_hp'] or '?'}KM {r['version'] or ''} | {r['mileage'] if r['mileage'] is not None else '?'} km | "
          f"{(r['seller_name'] or '')[:28]} {r['city'] or ''}{flag}")
        p(f"            {r['url']}")
    p("\nТоп-3 по совпадению с ориентиром:")
    for r in top[:3]:
        p(f"  {r['match_score']:3d}/100 {fmt(r['cost_for_me'])} {unit} | {', '.join(r['match_why'])} | {r['url']}")
    c = changes
    if meta["prev_run"]:
        p(f"\nС прошлого запуска ({meta['prev_run']}): новых {len(c['new'])}, подешевели {len(c['price_down'])}, "
          f"подорожали {len(c['price_up'])}, исчезли {len(c['gone'])}")
        for r in c["price_down"][:5]:
            p(f"  ↓ {fmt(r['old_price'])} → {fmt(r['price_listed'])}  {r['url']}")
        for r in c["new"][:5]:
            p(f"  + {fmt(r['price_listed'])}  {r['title'][:60]}  {r['url']}")
    else:
        p("\nПервый запуск — история изменений появится со следующего.")
    p(f"\nОтчёт: {out_dir / 'report.html'}   CSV: {out_dir / 'listings.csv'}")


if __name__ == "__main__":
    sys.exit(run())
