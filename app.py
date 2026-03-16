import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

RIOT_API_KEY = os.getenv("RIOT_API_KEY")

REGION = "euw1"
MATCH_REGION = "europe"

def riot_get(url):
    headers = {"X-Riot-Token": RIOT_API_KEY}
    r = requests.get(url, headers=headers)
    return r.json()

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def search():
    player = request.args.get("player")

    if "#" not in player:
        return "Use format: Name#TAG"

    name, tag = player.split("#")

    # account
    acc = riot_get(
        f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    )

    puuid = acc["puuid"]

    # summoner
    summ = riot_get(
        f"https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )

    # matches
    matches = riot_get(
        f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
    )

    games = []

    for m in matches:

        data = riot_get(
            f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{m}"
        )

        info = data["info"]

        players = info["participants"]

        teams = {"blue": [], "red": []}

        mvp = None
        best_score = 0

        for p in players:

            kda = (p["kills"] + p["assists"]) / max(1, p["deaths"])

            if kda > best_score:
                best_score = kda
                mvp = p

            player_data = {
                "champion": p["championName"],
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
                "gold": p["goldEarned"],
                "item0": p["item0"],
                "item1": p["item1"],
                "item2": p["item2"],
                "item3": p["item3"],
                "item4": p["item4"],
                "item5": p["item5"],
            }

            if p["teamId"] == 100:
                teams["blue"].append(player_data)
            else:
                teams["red"].append(player_data)

        games.append(
            {
                "mode": info["gameMode"],
                "blue": teams["blue"],
                "red": teams["red"],
                "mvp": mvp["championName"],
            }
        )

    return render_template(
        "results.html",
        games=games,
        summoner=summ
    )


if __name__ == "__main__":
    app.run()
