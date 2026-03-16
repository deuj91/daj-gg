import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

REGION = "euw1"
MATCH_REGION = "europe"

def riot_get(url):
    headers = {"X-Riot-Token": API_KEY}
    r = requests.get(url, headers=headers)
    return r.json()

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if "#" not in player:
        return "Use Name#TAG"

    name, tag = player.split("#")

    acc = riot_get(
        f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    )

    puuid = acc["puuid"]

    summ = riot_get(
        f"https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )

    matches = riot_get(
        f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=20"
    )

    games = []

    for m in matches:

        data = riot_get(
            f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{m}"
        )

        info = data["info"]

        duration = round(info["gameDuration"] / 60)

        for p in info["participants"]:

            if p["puuid"] == puuid:

                games.append({

                    "champ": p["championName"],
                    "kills": p["kills"],
                    "deaths": p["deaths"],
                    "assists": p["assists"],
                    "win": p["win"],
                    "gold": p["goldEarned"],
                    "items":[
                        p["item0"],
                        p["item1"],
                        p["item2"],
                        p["item3"],
                        p["item4"],
                        p["item5"],
                        p["item6"]
                    ],
                    "duration": duration,
                    "mode": info["gameMode"]

                })

    return render_template(
        "results.html",
        games=games,
        summoner=summ
    )

if __name__ == "__main__":
    app.run()
