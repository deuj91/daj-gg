import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

REGION_SUMMONER = "https://euw1.api.riotgames.com"
REGION_ACCOUNT = "https://europe.api.riotgames.com"
REGION_MATCH = "https://europe.api.riotgames.com"


def riot_get(url):
    headers = {"X-Riot-Token": API_KEY}
    r = requests.get(url, headers=headers)
    return r.json()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if "#" not in player:
        return "Use name#tag"

    name, tag = player.split("#")

    acc = riot_get(
        f"{REGION_ACCOUNT}/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    )

    puuid = acc["puuid"]

    summ = riot_get(
        f"{REGION_SUMMONER}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )

    match_ids = riot_get(
        f"{REGION_MATCH}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10"
    )

    games = []

    for mid in match_ids:

        match = riot_get(
            f"{REGION_MATCH}/lol/match/v5/matches/{mid}"
        )

        info = match["info"]

        blue = []
        red = []

        for p in info["participants"]:

            pdata = {
                "name": p["summonerName"],
                "champ": p["championName"],
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
                "gold": p["goldEarned"],
                "items": [
                    p["item0"], p["item1"], p["item2"],
                    p["item3"], p["item4"], p["item5"]
                ]
            }

            if p["teamId"] == 100:
                blue.append(pdata)
            else:
                red.append(pdata)

        games.append({
            "mode": info["gameMode"],
            "duration": int(info["gameDuration"] / 60),
            "blue": blue,
            "red": red
        })

    return render_template(
        "results.html",
        games=games,
        summoner=summ
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
