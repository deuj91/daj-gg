import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

RIOT_API_KEY = os.getenv("RIOT_API_KEY")

REGION_ACCOUNT = "https://europe.api.riotgames.com"
REGION_MATCH = "https://europe.api.riotgames.com"
REGION_SUMMONER = "https://euw1.api.riotgames.com"


def get_puuid(name, tag):
    url = f"{REGION_ACCOUNT}/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return None

    return r.json()["puuid"]


def get_summoner(puuid):
    url = f"{REGION_SUMMONER}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return None

    return r.json()


def get_matches(puuid):
    url = f"{REGION_MATCH}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=20"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return []

    return r.json()


def get_match(match_id):
    url = f"{REGION_MATCH}/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return None

    return r.json()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if "#" not in player:
        return "Format: pseudo#TAG"

    name, tag = player.split("#")

    puuid = get_puuid(name, tag)

    if not puuid:
        return "Player not found"

    summ = get_summoner(puuid)

    matches = get_matches(puuid)

    games = []

    for m in matches:

        data = get_match(m)

        if not data:
            continue

        info = data["info"]

        for p in info["participants"]:
            if p["puuid"] == puuid:

                items = [
                    p["item0"],
                    p["item1"],
                    p["item2"],
                    p["item3"],
                    p["item4"],
                    p["item5"],
                ]

                games.append({
                    "champ": p["championName"],
                    "kills": p["kills"],
                    "deaths": p["deaths"],
                    "assists": p["assists"],
                    "win": p["win"],
                    "items_list": items,
                    "duration": int(info["gameDuration"] / 60)
                })

    return render_template(
        "results.html",
        games=games,
        summoner=summ
    )


if __name__ == "__main__":
    app.run()
