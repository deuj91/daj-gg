from flask import Flask, render_template, request
import requests
import time
import os

app = Flask(__name__)

API_KEY = os.environ.get("RIOT_API_KEY")

REGION = "euw1"
MATCH_REGION = "europe"

session = requests.Session()

CACHE = {}
CACHE_TIME = 300


def ai_coach(games):

    tips = []

    kills = sum(g["kills"] for g in games)
    deaths = sum(g["deaths"] for g in games)
    assists = sum(g["assists"] for g in games)

    avg_kills = kills / len(games)
    avg_deaths = deaths / len(games)

    kda = (kills + assists) / max(1, deaths)

    if avg_deaths > 7:
        tips.append("You die too much. Try safer positioning.")

    if avg_kills < 4:
        tips.append("Your impact is low. Try roaming more.")

    if kda > 4:
        tips.append("Great KDA. You are performing well.")

    if not tips:
        tips.append("Balanced performance. Improve map awareness.")

    return tips


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player:
        return "Player missing"

    if player in CACHE:

        data, t = CACHE[player]

        if time.time() - t < CACHE_TIME:
            return render_template(
                "profile.html",
                name=player,
                games=data["games"],
                tips=data["tips"]
            )

    if "#" not in player:
        return "Use RiotID format Name#TAG"

    name, tag = player.split("#")

    url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"

    acc = session.get(url, headers={"X-Riot-Token": API_KEY}).json()

    puuid = acc["puuid"]

    matches_url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=10"

    match_ids = session.get(matches_url, headers={"X-Riot-Token": API_KEY}).json()

    games = []

    for match_id in match_ids:

        murl = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"

        match = session.get(murl, headers={"X-Riot-Token": API_KEY}).json()

        participants = match["metadata"]["participants"]
        info = match["info"]["participants"]

        players = []

        for p in info:

            players.append({

                "name": p["riotIdGameName"],
                "champion": p["championName"],
                "items": [
                    p["item0"],
                    p["item1"],
                    p["item2"],
                    p["item3"],
                    p["item4"],
                    p["item5"]
                ]

            })

        me = next(p for p in info if p["puuid"] == puuid)

        games.append({

            "champion": me["championName"],
            "kills": me["kills"],
            "deaths": me["deaths"],
            "assists": me["assists"],
            "win": me["win"],
            "players": players

        })

    tips = ai_coach(games)

    CACHE[player] = (
        {
            "games": games,
            "tips": tips
        },
        time.time()
    )

    return render_template(
        "profile.html",
        name=player,
        games=games,
        tips=tips
    )


if __name__ == "__main__":
    app.run()
