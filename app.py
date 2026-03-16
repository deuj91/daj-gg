import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

ACCOUNT_REGION = "europe"
MATCH_REGION = "europe"
PLATFORM = "euw1"


def riot_get(url):
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
        return "Use format: name#tag"

    name, tag = player.split("#")

    account = riot_get(
        f"https://{ACCOUNT_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    )

    if not account or "puuid" not in account:
        return "Player not found"

    puuid = account["puuid"]

    summoner = riot_get(
        f"https://{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )

    if not summoner:
        return "Summoner error"

    ranked = riot_get(
        f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    )

    rank = ranked[0] if ranked and len(ranked) > 0 else None

    match_ids = riot_get(
        f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=20"
    )

    games = []

    if match_ids:

        for match_id in match_ids:

            match = riot_get(
                f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            )

            if not match:
                continue

            info = match["info"]

            player = None

            for p in info["participants"]:
                if p["puuid"] == puuid:
                    player = p
                    break

            if not player:
                continue

            items_list = [
                player["item0"],
                player["item1"],
                player["item2"],
                player["item3"],
                player["item4"],
                player["item5"]
            ]

            games.append({
                "champ": player["championName"],
                "kills": player["kills"],
                "deaths": player["deaths"],
                "assists": player["assists"],
                "win": player["win"],
                "duration": int(info["gameDuration"]/60),
                "items_list": items_list
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
