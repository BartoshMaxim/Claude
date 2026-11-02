"""SQLite: объявления, история цен, запуски, статус источников."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .model import Listing

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
  uid TEXT PRIMARY KEY,
  platform TEXT, kind TEXT, url TEXT, title TEXT,
  price_listed REAL, price_net REAL, price_gross REAL, price_basis TEXT, invoice_vat INTEGER,
  real_price_net REAL, real_price_gross REAL, real_price_note TEXT,
  fleet_flag INTEGER, fleet_phrases TEXT,
  year INTEGER, model_year INTEGER, mileage INTEGER, engine_cc INTEGER, power_hp INTEGER,
  fuel TEXT, gearbox TEXT, version TEXT, trim TEXT, seats INTEGER, city TEXT,
  seller_type TEXT, seller_name TEXT, posted_at TEXT, condition TEXT, vin TEXT,
  external_ref TEXT, monthly_rate_net REAL, lease_terms TEXT, price_drop_pct REAL,
  description TEXT, dedup_key TEXT, duplicates TEXT,
  match_score INTEGER, match_why TEXT, cost_for_me REAL, cost_basis TEXT,
  first_seen TEXT, last_seen TEXT, active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS price_history (
  uid TEXT, seen_at TEXT, price_listed REAL, price_net REAL, price_gross REAL,
  PRIMARY KEY (uid, seen_at)
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, started TEXT, finished TEXT, pages INTEGER, summary TEXT
);
CREATE TABLE IF NOT EXISTS source_status (
  run_id INTEGER, source TEXT, status TEXT, note TEXT, found INTEGER
);
"""

COLS = ["platform", "kind", "url", "title", "price_listed", "price_net", "price_gross", "price_basis",
        "invoice_vat", "real_price_net", "real_price_gross", "real_price_note", "fleet_flag",
        "fleet_phrases", "year", "model_year", "mileage", "engine_cc", "power_hp", "fuel", "gearbox",
        "version", "trim", "seats", "city", "seller_type", "seller_name", "posted_at", "condition",
        "vin", "external_ref", "monthly_rate_net", "lease_terms", "price_drop_pct", "description"]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class DB:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)

    def start_run(self) -> int:
        cur = self.con.execute("INSERT INTO runs(started) VALUES (?)", (now(),))
        self.con.commit()
        return cur.lastrowid

    def previous_run_time(self, run_id: int) -> str | None:
        r = self.con.execute("SELECT started FROM runs WHERE id < ? AND finished IS NOT NULL "
                             "ORDER BY id DESC LIMIT 1", (run_id,)).fetchone()
        return r["started"] if r else None

    def finish_run(self, run_id: int, pages: int, summary: dict):
        self.con.execute("UPDATE runs SET finished=?, pages=?, summary=? WHERE id=?",
                         (now(), pages, json.dumps(summary, ensure_ascii=False), run_id))
        self.con.commit()

    def source_status(self, run_id: int, source: str, status: str, note: str, found: int):
        self.con.execute("INSERT INTO source_status VALUES (?,?,?,?,?)", (run_id, source, status, note, found))

    def get(self, uid: str):
        return self.con.execute("SELECT * FROM listings WHERE uid=?", (uid,)).fetchone()

    def upsert(self, l: Listing, ts: str, extra: dict) -> dict:
        """Сохраняет объявление; возвращает {'new': bool, 'old_price': float|None}."""
        old = self.get(l.uid)
        vals = {c: getattr(l, c) for c in COLS}
        vals["fleet_phrases"] = json.dumps(l.fleet_phrases, ensure_ascii=False)
        vals["invoice_vat"] = None if l.invoice_vat is None else int(l.invoice_vat)
        vals["fleet_flag"] = int(l.fleet_flag)
        vals.update(extra)
        if old is None:
            vals.update(uid=l.uid, first_seen=ts, last_seen=ts, active=1)
            keys = list(vals)
            self.con.execute(f"INSERT INTO listings({','.join(keys)}) VALUES ({','.join('?' * len(keys))})",
                             [vals[k] for k in keys])
        else:
            if not l.description and old["description"]:
                vals["description"] = old["description"]   # детали могли не загрузиться в этот раз
            vals.update(last_seen=ts, active=1)
            sets = ",".join(f"{k}=?" for k in vals)
            self.con.execute(f"UPDATE listings SET {sets} WHERE uid=?", [*vals.values(), l.uid])
        last = self.con.execute("SELECT price_listed FROM price_history WHERE uid=? ORDER BY seen_at DESC LIMIT 1",
                                (l.uid,)).fetchone()
        if last is None or (l.price_listed and last["price_listed"] != l.price_listed):
            self.con.execute("INSERT OR REPLACE INTO price_history VALUES (?,?,?,?,?)",
                             (l.uid, ts, l.price_listed, l.price_net, l.price_gross))
        return {"new": old is None, "old_price": last["price_listed"] if last else None}

    def mark_inactive(self, platforms_ok: list[str], ts: str) -> list[sqlite3.Row]:
        """Объявления успешно опрошенных платформ, не встреченные в этом запуске."""
        if not platforms_ok:
            return []
        q = ",".join("?" * len(platforms_ok))
        gone = self.con.execute(f"SELECT * FROM listings WHERE active=1 AND last_seen<? AND platform IN ({q})",
                                (ts, *platforms_ok)).fetchall()
        self.con.execute(f"UPDATE listings SET active=0 WHERE active=1 AND last_seen<? AND platform IN ({q})",
                         (ts, *platforms_ok))
        return gone

    def history(self, uid: str) -> list[tuple[str, float]]:
        return [(r["seen_at"], r["price_listed"]) for r in
                self.con.execute("SELECT seen_at, price_listed FROM price_history WHERE uid=? ORDER BY seen_at",
                                 (uid,))]

    def active(self) -> list[sqlite3.Row]:
        return self.con.execute("SELECT * FROM listings WHERE active=1").fetchall()

    def commit(self):
        self.con.commit()
