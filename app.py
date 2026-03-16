from flask import Flask, render_template, request
import requests
import os
import time

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")
headers = {"X-Riot-Token": API_KEY}

CACHE = {}
CACHE_TIME = 120

VERSION = "14.6.1"


def get_cache(key):
    if key in CACHE:
        data, timestamp = CACHE[key]
        if time.time() - timestamp < CACHE_TIME:
            return data
    return None


def set_cache(key, value):
    CACHE[key] = (value, time.time())


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def search():

    player_input = request.args.get("player")

    if not player_input or "#" not in player_input:
        return "Format: Name#TAG"

    name, tag = player_input.split("#")

    cache_key = f"{name}#{tag}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    account = requests.get(
        f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
        headers=headers
    ).json()

    puuid = account["puuid"]

    summoner = requests.get(
        f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}",
        headers=headers
    ).json()

    icon = summoner["profileIconId"]
    level = summoner["summonerLevel"]

    rank = "Unranked"

    leagues = requests.get(
        f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}",
        headers=headers
    ).json()

    for r in leagues:
        if r["queueType"] == "RANKED_SOLO_5x5":
            rank = f'{r["tier"]} {r["rank"]} {r["leaguePoints"]} LP'

    match_ids = requests.get(
        f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5",
        headers=headers
    ).json()

    matches = []

    for match_id in match_ids:

        data = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
            headers=headers
        ).json()

        info = data["info"]

        teams = {"blue": [], "red": []}

        for p in info["participants"]:

            build = [
                p["item0"],
                p["item1"],
                p["item2"],
                p["item3"],
                p["item4"],
                p["item5"]
            ]

            player_data = {
                "name": p.get("riotIdGameName", "Unknown"),
                "champion": p["championName"],
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
                "build": build,
                "win": p["win"]
            }

            if p["teamId"] == 100:
                teams["blue"].append(player_data)
            else:
                teams["red"].append(player_data)

        matches.append({"teams": teams})

    bg = matches[0]["teams"]["blue"][0]["champion"]

    html = render_template(
        "profile.html",
        name=name,
        tag=tag,
        level=level,
        icon=icon,
        rank=rank,
        matches=matches,
        bg=bg
    )

    set_cache(cache_key, html)

    return html


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
