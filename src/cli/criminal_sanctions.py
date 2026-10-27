"""Derive structured sanctions from the latest imported УК РФ edition.

Usage: python -m src.cli.criminal_sanctions import [--act uk-rf]
"""

import argparse
import asyncio
import json

from src.db.session import async_session_factory
from src.services.criminal_sanction_import import import_criminal_sanctions, latest_edition_id


async def run_import(act_key: str) -> dict:
    async with async_session_factory() as db:
        edition_id = await latest_edition_id(db, act_key)
        if edition_id is None:
            raise SystemExit(f"no imported edition for act {act_key!r}")
        return {"edition_id": edition_id, **await import_criminal_sanctions(db, edition_id)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("import", help="parse sanctions of every article")
    command.add_argument("--act", default="uk-rf")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_import(args.act)), ensure_ascii=False))


if __name__ == "__main__":
    main()
