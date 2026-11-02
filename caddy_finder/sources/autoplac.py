"""autoplac.pl — на момент разработки (ноябрь 2026) сайт отвечает
Cloudflare-челленджем («Just a moment… / Cierpliwości…») даже на robots.txt,
и для requests, и для headless-браузера. Обход челленджа не делаем.

Модуль при каждом запуске только проверяет доступность robots.txt: если когда-нибудь
сайт начнёт отвечать — в отчёте будет видно, и парсер можно дописать.
"""
from __future__ import annotations

from ..http import Blocked

NAME = "autoplac"
BASE = "https://autoplac.pl"


def fetch(client, cfg: dict, status: dict, prefilter):
    rob = client.load_robots(BASE + "/")
    if rob is None:
        raise Blocked("autoplac.pl: robots.txt недоступен (Cloudflare challenge) — сайт не трогаем")
    status["note"] = "robots.txt доступен, но парсер не реализован — сайт ранее блокировал запросы"
    return []
