"""Вежливый HTTP-клиент: robots.txt, задержки, лимит страниц, файловый кэш.

Два транспорта:
  * requests — по умолчанию;
  * Playwright (Chromium) — для сайтов, которые отдают данные только обычному
    браузеру (без логина и без решения капчи). Если в ответе капча/челлендж —
    источник помечается как заблокированный, обход не делается.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)

CHALLENGE_MARKERS = (
    "Just a moment...", "cf-mitigated", "challenges.cloudflare.com", "Human Verification",
    "Cierpliwości...", "captcha-delivery", "g-recaptcha", "hcaptcha",
)


class BudgetExceeded(Exception):
    pass


class Blocked(Exception):
    """Сайт ответил капчей/челленджем/403 — дальше не идём."""


class Disallowed(Exception):
    """Путь запрещён robots.txt."""


@dataclass
class Response:
    url: str
    status: int
    text: str
    from_cache: bool

    def json(self):
        return json.loads(self.text)


# ---------------------------------------------------------------- robots.txt
class Robots:
    """Минимальный парсер robots.txt с семантикой Google: * и $, самое длинное
    совпадение побеждает, при равенстве — Allow. (urllib.robotparser не умеет
    wildcard'ы в середине пути.)"""

    def __init__(self, text: str):
        self.rules: list[tuple[bool, str]] = []
        groups: list[tuple[list[str], list[tuple[bool, str]]]] = []
        agents: list[str] = []
        rules: list[tuple[bool, str]] = []
        last_was_rule = False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, val = (p.strip() for p in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if last_was_rule:
                    groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(val.lower())
                last_was_rule = False
            elif key in ("allow", "disallow"):
                last_was_rule = True
                if val:
                    rules.append((key == "allow", val))
        if agents:
            groups.append((agents, rules))
        for ags, rls in groups:
            if "*" in ags:
                self.rules.extend(rls)

    @staticmethod
    def _to_regex(pattern: str) -> re.Pattern:
        anchored = pattern.endswith("$")
        if anchored:
            pattern = pattern[:-1]
        rx = "".join(".*" if ch == "*" else re.escape(ch) for ch in pattern)
        return re.compile(rx + ("$" if anchored else ""))

    def allowed(self, path_and_query: str) -> bool:
        best_len, best_allow = -1, True
        for allow, pat in self.rules:
            if self._to_regex(pat).match(path_and_query):
                ln = len(pat)
                if ln > best_len or (ln == best_len and allow):
                    best_len, best_allow = ln, allow
        return best_allow


# ---------------------------------------------------------------- client
class PoliteClient:
    def __init__(self, cfg: dict):
        pol = cfg["politeness"]
        self.ua = pol["user_agent"]
        self.delay = (float(pol["delay_min"]), float(pol["delay_max"]))
        self.max_pages = int(pol["max_pages"])
        self.cache_dir = Path(cfg["paths"]["cache_dir"]) / "http"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pages_fetched = 0
        self._last_hit: dict[str, float] = {}
        self._robots: dict[str, Robots | None] = {}
        self.robots_text: dict[str, str] = {}
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.ua,
            "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.6",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        })
        self._pw = None
        self._browser = None
        self._page = None

    # ------------------------------------------------ helpers
    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".json")

    def cache_get(self, url: str, max_age_s: float | None) -> Response | None:
        p = self._cache_path(url)
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text())
        except Exception:
            return None
        if max_age_s is not None and time.time() - d["fetched_at"] > max_age_s:
            return None
        return Response(url, d["status"], d["body"], True)

    def _cache_put(self, url: str, status: int, body: str):
        self._cache_path(url).write_text(json.dumps(
            {"url": url, "fetched_at": time.time(), "status": status, "body": body}))

    def _wait_turn(self, host: str):
        last = self._last_hit.get(host)
        if last is not None:
            gap = random.uniform(*self.delay)
            sleep = last + gap - time.time()
            if sleep > 0:
                time.sleep(sleep)
        self._last_hit[host] = time.time()

    def _spend(self):
        if self.pages_fetched >= self.max_pages:
            raise BudgetExceeded(f"достигнут лимит {self.max_pages} страниц за запуск")
        self.pages_fetched += 1

    @staticmethod
    def looks_like_challenge(text: str) -> bool:
        head = text[:20000]
        return any(m in head for m in CHALLENGE_MARKERS)

    # ------------------------------------------------ robots
    def load_robots(self, base: str, use_browser: bool = False) -> Robots | None:
        """Возвращает Robots или None, если robots.txt недоступен (тогда сайт не трогаем)."""
        host = urlsplit(base).netloc
        if host in self._robots:
            return self._robots[host]
        url = f"{urlsplit(base).scheme}://{host}/robots.txt"
        text, status = None, None
        cached = self.cache_get(url, 24 * 3600)
        if cached and cached.status == 200:
            text, status = cached.text, 200
        else:
            try:
                self._spend()
                self._wait_turn(host)
                if use_browser:
                    text, status = self._browser_get_text(url)
                else:
                    r = self.session.get(url, timeout=30)
                    text, status = r.text, r.status_code
            except BudgetExceeded:
                raise
            except Exception as e:  # noqa: BLE001
                log.warning("robots.txt %s: %s", url, e)
            if status == 200 and text and not self.looks_like_challenge(text):
                self._cache_put(url, 200, text)
            else:
                text = None
        rob = Robots(text) if text else None
        self._robots[host] = rob
        if text:
            self.robots_text[host] = text
        return rob

    def check_allowed(self, url: str, use_browser: bool = False):
        rob = self.load_robots(url, use_browser=use_browser)
        if rob is None:
            raise Blocked(f"robots.txt недоступен для {urlsplit(url).netloc} — сайт не трогаем")
        parts = urlsplit(url)
        pq = parts.path + (("?" + parts.query) if parts.query else "")
        if not rob.allowed(pq):
            raise Disallowed(f"robots.txt запрещает {pq}")

    # ------------------------------------------------ fetch
    def get(self, url: str, max_age_s: float | None = 6 * 3600, browser: bool = False) -> Response:
        cached = self.cache_get(url, max_age_s)
        if cached:
            return cached
        self.check_allowed(url, use_browser=browser)
        self._spend()
        host = urlsplit(url).netloc
        self._wait_turn(host)
        log.debug("GET %s", url)
        if browser:
            text, status = self._browser_get_text(url)
        else:
            r = self.session.get(url, timeout=40)
            text, status = r.text, r.status_code
        if status in (403, 405, 429) or self.looks_like_challenge(text):
            raise Blocked(f"{host}: HTTP {status}, похоже на капчу/блокировку")
        if status != 200:
            raise RuntimeError(f"{url}: HTTP {status}")
        self._cache_put(url, status, text)
        return Response(url, status, text, False)

    # ------------------------------------------------ browser
    def _ensure_browser(self):
        if self._page is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch()
            ctx = self._browser.new_context(user_agent=self.ua, locale="pl-PL")
            self._page = ctx.new_page()
        return self._page

    def _browser_get_text(self, url: str) -> tuple[str, int]:
        page = self._ensure_browser()
        resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
        status = resp.status if resp else 0
        ctype = (resp.headers.get("content-type", "") if resp else "")
        if "json" in ctype or url.endswith(".txt"):
            body = resp.text()
        else:
            body = page.content()
        return body, status

    def close(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:  # noqa: BLE001
            pass
