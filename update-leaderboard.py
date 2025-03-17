import asyncio
import httpx
import json
from datetime import datetime, timedelta, timezone

BASE_URL = "https://api.wiseoldman.net/v2"
NAMES_FILE = "names.txt"
OUTPUT_FILE = "leaderboard.json"

# Set the fixed start time (March 14, 2025, at 16:00 UTC)
START_DATE = "2025-03-14T16:00:00.000Z"

def round_to_next_hour(dt):
    return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

def convert_to_utc_string(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def load_usernames():
    with open(NAMES_FILE, "r", encoding="utf-8") as file:
        teams = json.load(file) 
    return teams


async def get_ehb(username, start_date, end_date, retries=3, delay=5):
    async with httpx.AsyncClient(timeout=30.0) as client: 
        for attempt in range(retries):
            try:
                response = await client.get(
                    f"{BASE_URL}/players/{username}/gained",
                    params={"startDate": start_date, "endDate": end_date}
                )
                response.raise_for_status()
                return response.json()

            except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
                print(f"Attempt {attempt+1} failed for {username}: {e}")
                if attempt < retries - 1: 
                    await asyncio.sleep(delay) 
                else:
                    print(f"Final failure for {username}, skipping.")

    return None 

async def calculate_ehb(username):
    if username.lower() == "oh kay den": 
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        start_date = convert_to_utc_string(start_time)
        end_date = convert_to_utc_string(end_time)
    else:
        end_date = convert_to_utc_string(round_to_next_hour(datetime.now(timezone.utc)))
        start_date = START_DATE

    gains = await get_ehb(username, start_date, end_date)

    if not gains or "data" not in gains:
        print("no gains or data")
        return 0 
    try:
        return round(gains["data"]["computed"]["ehb"]["value"]["gained"], 2)
    except KeyError:
        return 0 

async def calculate_leaderboard():
    teams = load_usernames()
    leaderboard = []
    team_totals = {}
    for team, usernames in teams.items():
        team_total = 0
        for username in usernames:
            
            ehb = await calculate_ehb(username)
            print(username,"has ehb of",ehb)
            leaderboard.append({"username": username, "team": team, "ehb": ehb})
            team_total += ehb

        team_totals[team] = round(team_total, 2)

    leaderboard.sort(key=lambda x: x["ehb"], reverse=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump({"teams": team_totals, "individuals": leaderboard}, file, indent=2)

asyncio.run(calculate_leaderboard())
