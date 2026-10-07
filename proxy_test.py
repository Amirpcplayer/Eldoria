import asyncio
import aiohttp


async def main():
    proxy = "http://127.0.0.1:10808"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.telegram.org",
            proxy=proxy,
            timeout=15,
        ) as response:
            print("Status:", response.status)
            print("URL:", response.url)


if __name__ == "__main__":
    asyncio.run(main())