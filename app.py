import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

REGION = "europe"
PLATFORM = "euw1"


def riot(url):
    headers = {"X-Riot-Token": API_KEY}
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

    if not player or "#" not in player:
        return "Use format name#tag"

    name, tag = player.split("#")

    account = riot(
        f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    )

    if not account:
        return "Player not found"

    puuid = account["puuid"]

    summoner = riot(
        f"https://{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )

    ranked = riot(
        f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    )

    rank = ranked[0] if ranked else None

    matches = riot(
        f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5"
    )

    games = []

    if matches:

        for match_id in matches:

            match = riot(
                f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            )

            if not match:
                continue

            info = match["info"]

            blue = []
            red = []

            for p in info["participants"]:

                data = {
                    "name": p["summonerName"],
                    "champ": p["championName"],
                    "kills": p["kills"],
                    "deaths": p["deaths"],
                    "assists": p["assists"],
                    "gold": p["goldEarned"],
                    "items": [
                        p["item0"],
                        p["item1"],
                        p["item2"],
                        p["item3"],
                        p["item4"],
                        p["item5"]
                    ]
                }

                if p["teamId"] == 100:
                    blue.append(data)
                else:
                    red.append(data)

            games.append({
                "mode": info["gameMode"],
                "duration": int(info["gameDuration"] / 60),
                "blue": blue,
                "red": red
            })

    return render_template(
        "results.html",
        games=games,
        summoner=summoner,
        rank=rank
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
