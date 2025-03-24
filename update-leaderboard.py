import asyncio
import httpx
import json
from datetime import datetime, timedelta, timezone

BASE_URL = "https://api.wiseoldman.net/v2"
NAMES_FILE = "names.txt"
OUTPUT_FILE = "leaderboard.json"

START_DATE = "2025-03-14T16:00:00.000Z"
START_DATE_OKD = "2025-03-12T16:00:00.000Z" #manual start date change due to missing WOM update - 0 gains prior to bingo
def round_to_next_hour(dt):
    return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

def convert_to_utc_string(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def load_usernames():
    with open(NAMES_FILE, "r", encoding="utf-8") as file:
        teams = json.load(file) 
    return teams


async def get_ehb(username, start_date, end_date, timeout=30):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{BASE_URL}/players/{username}/gained",
            params={"startDate": start_date, "endDate": end_date}
        )
        if response.status_code == 200:
            return response.json()
        return None

async def calculate_ehb(username):
    end_date = convert_to_utc_string(round_to_next_hour(datetime.now(timezone.utc)))
    if username.lower() == "oh kay den": 
        start_date = START_DATE_OKD
    else:
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
            #print(username, "has ehb of", ehb)
            leaderboard.append({"username": username, "team": team, "ehb": ehb})
            team_total += ehb

        team_totals[team] = round(team_total, 2)

    sorted_team_totals = dict(sorted(team_totals.items(), key=lambda item: item[1], reverse=True))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump({"teams": sorted_team_totals, "individuals": leaderboard}, file, indent=2)

asyncio.run(calculate_leaderboard())
