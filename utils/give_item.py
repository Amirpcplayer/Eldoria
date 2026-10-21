"""Grant an item to a player explicitly selected by CLI arguments.

Example:
    python -m utils.give_item --telegram-id 123456789 --item "معجون سلامتی" --quantity 3

No player ID or quantity is hard-coded, to prevent accidental grants in production.
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.item import Item
from services.inventory_service import add_item


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grant an inventory item to a World Eldoria player.")
    parser.add_argument("--telegram-id", type=int, required=True, help="Telegram numeric ID of the target player")
    parser.add_argument("--item", required=True, help="Exact item name as stored in the database")
    parser.add_argument("--quantity", type=int, default=1, help="Positive quantity to grant (default: 1)")
    args = parser.parse_args()
    if args.telegram_id <= 0:
        parser.error("--telegram-id must be a positive integer")
    if args.quantity <= 0:
        parser.error("--quantity must be a positive integer")
    if not args.item.strip():
        parser.error("--item cannot be empty")
    return args


async def give_item(telegram_id: int, item_name: str, quantity: int) -> int:
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id)
        )
        if character is None:
            print("❌ Character not found.")
            return 1

        item = await session.scalar(select(Item).where(Item.name == item_name))
        if item is None:
            print("❌ Item not found. Use the exact database item name.")
            return 1

        character_id = character.id
        item_id = item.id
        character_name = character.name

    success = await add_item(
        character_id=character_id,
        item_id=item_id,
        quantity=quantity,
    )
    if not success:
        print("❌ Failed to add item.")
        return 1

    print(f"✅ Granted {quantity}x {item_name} to {character_name} (Telegram ID {telegram_id}).")
    return 0


if __name__ == "__main__":
    options = parse_args()
    raise SystemExit(asyncio.run(give_item(options.telegram_id, options.item.strip(), options.quantity)))
