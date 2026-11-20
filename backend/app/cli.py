"""Command-line helpers.

    python -m app.cli crawl              # crawl all airlines once, in the foreground
    python -m app.cli crawl --airlines UA,WN
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from . import db
from .crawler import Crawler


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    crawl = sub.add_parser("crawl", help="run one crawl now")
    crawl.add_argument("--airlines", help="comma-separated codes, e.g. UA,AC")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    with db.connect() as conn:
        db.init_db(conn)
    if args.command == "crawl":
        codes = [c.strip().upper() for c in args.airlines.split(",")] if args.airlines else None
        asyncio.run(Crawler().run(codes))


if __name__ == "__main__":
    main()
