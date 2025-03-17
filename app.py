import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, send_from_directory
import json
import os

app = Flask(__name__)
BASE_URL = "https://api.wiseoldman.net/v2"

START_TIME = datetime(2025, 3, 14, 14, 0, tzinfo=timezone.utc)

now = datetime.now(timezone.utc)
rounded_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

def convert_to_utc_string(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

START_DATE = convert_to_utc_string(START_TIME)
END_DATE = convert_to_utc_string(rounded_hour)

def load_usernames(filename="names.txt"):
    with open(filename, "r") as file:
        return json.load(file)

async def get_ehb(username, start_date, end_date):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players/{username}/gained?startDate={start_date}&endDate={end_date}"
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data for {username}: {response.status_code}")
            return None

async def calculate_ehb(username):
    if username.lower() == "oh kay den": # initial wise old man update missing
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        start_date = convert_to_utc_string(start_time)
        end_date = convert_to_utc_string(end_time)

        gains = await get_ehb(username, start_date, end_date)
    else:
        gains = await get_ehb(username, START_DATE, END_DATE)

    if not gains or "data" not in gains:
        return 0 
    try:
        return round(gains["data"]["computed"]["ehb"]["value"]["gained"], 2)
    except KeyError:
        return 0 

async def calculate_individual_leaderboards():
    usernames_dict = load_usernames() 
    individual_ehb = {}

    tasks = []
    for team, usernames in usernames_dict.items():
        for username in usernames:
            tasks.append((team, username, calculate_ehb(username)))

    results = await asyncio.gather(*(task[2] for task in tasks)) 

    for i, (team, username, _) in enumerate(tasks):
        ehb = results[i]
        individual_ehb[username] = ehb

    # Sort the leaderboard
    sorted_individuals = sorted(individual_ehb.items(), key=lambda x: x[1], reverse=True)
    return sorted_individuals

async def calculate_team_leaderboards():
    usernames_dict = load_usernames() 
    team_ehb = {team: 0 for team in usernames_dict}

    tasks = []
    for team, usernames in usernames_dict.items():
        for username in usernames:
            tasks.append((team, username, calculate_ehb(username)))

    results = await asyncio.gather(*(task[2] for task in tasks))

    for i, (team, username, _) in enumerate(tasks):
        ehb = results[i]
        team_ehb[team] += ehb

    team_ehb = {team: round(ehb, 2) for team, ehb in team_ehb.items()}
    sorted_teams = sorted(team_ehb.items(), key=lambda x: x[1], reverse=True)
    return sorted_teams

@app.route('/')
def serve_home():
    try:
        return send_from_directory(os.getcwd(), 'index.html')
    except Exception as e:
        return f"Error loading index.html: {str(e)}"

@app.route('/leaderboards')
def get_leaderboards():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    individual_data = loop.run_until_complete(calculate_individual_leaderboards())
    team_data = loop.run_until_complete(calculate_team_leaderboards())

    return jsonify({
        "individuals": [{"rank": i+1, "username": user, "ehb": ehb} for i, (user, ehb) in enumerate(individual_data)],
        "teams": [{"rank": i+1, "team": team, "ehb": ehb} for i, (team, ehb) in enumerate(team_data)]
    })

if __name__ == '__main__':
    app.run(debug=True)
