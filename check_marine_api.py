
import asyncio
import httpx
import json


async def main():
    url = "https://marine-api.open-meteo.com/v1/marine"

    params = {
        "latitude": 15.0,
        "longitude": 72.0,
        "hourly": "wave_height",
        "forecast_days": 1,
        "timezone": "GMT",
        "length_unit": "metric",
        "cell_selection": "sea",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)

    print("HTTP status:", response.status_code)
    print("Request URL:", response.url)
    print(json.dumps(response.json(), indent=2)[:10000])


if __name__ == "__main__":
    asyncio.run(main())

