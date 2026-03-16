import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_KEY = os.environ.get("RIOT_API_KEY")

REGION = "europe"
MATCH_REGION = "europe"
PLATFORM = "euw1"

def riot(url):
    headers = {
        "X-Riot-Token": API_KEY
    }
    r = requests.get(f"https://{url}", headers=headers)
    return r.json()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if "#" not in player:
        return "Use format: Name#TAG"

    name, tag = player.split("#")

    # account by riot id
    acc = riot(f"{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}")

    if "puuid" not in acc:
        return "Player not found"

    puuid = acc["puuid"]

    # summoner info
    summ = riot(f"{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}")

    # ranked
    ranked = riot(f"{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}")

    rank = None
    if isinstance(ranked, list) and len(ranked) > 0:
        rank = ranked[0]

    # match history
    matches = riot(f"{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=20")

    games = []

    for m in matches:

        match = riot(f"{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{m}")

        info = match["info"]
        participants = info["participants"]

        player_data = None

        for p in participants:
            if p["puuid"] == puuid:
                player_data = p
                break

        if not player_data:
            continue

        items = [
            player_data["item0"],
            player_data["item1"],
            player_data["item2"],
            player_data["item3"],
            player_data["item4"],
            player_data["item5"],
        ]

        games.append({
            "champion": player_data["championName"],
            "kills": player_data["kills"],
            "deaths": player_data["deaths"],
            "assists": player_data["assists"],
            "win": player_data["win"],
            "items": items,
            "duration": int(info["gameDuration"] / 60)
        })

    return render_template(
        "results.html",
        games=games,
        summoner=summ,
        rank=rank
    )


if __name__ == "__main__":
    app.run()
