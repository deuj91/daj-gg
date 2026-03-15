from flask import Flask, render_template, request
import requests
import os

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player or "#" not in player:
        return "Use format: name#tag"

    name, tag = player.split("#")

    # ACCOUNT
    account = requests.get(
        f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
        headers={"X-Riot-Token": API_KEY}
    ).json()

    if "puuid" not in account:
        return "Player not found"

    puuid = account["puuid"]

    # SUMMONER
    summoner = requests.get(
        f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}",
        headers={"X-Riot-Token": API_KEY}
    ).json()

    icon = summoner.get("profileIconId", 0)
    level = summoner.get("summonerLevel", 0)

    # MATCH LIST
    matches = requests.get(
        f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5",
        headers={"X-Riot-Token": API_KEY}
    ).json()

    games = []

    for match_id in matches:

        match = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
            headers={"X-Riot-Token": API_KEY}
        ).json()

        info = match["info"]

        participants = info["participants"]

        player_data = next(p for p in participants if p["puuid"] == puuid)

        games.append({
            "champion": player_data["championName"],
            "kills": player_data["kills"],
            "deaths": player_data["deaths"],
            "assists": player_data["assists"],
            "win": player_data["win"]
        })

    return render_template(
        "profile.html",
        name=player,
        icon=icon,
        level=level,
        games=games
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
