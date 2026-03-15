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
        return "Use format name#tag"

    name, tag = player.split("#")

    # ACCOUNT
    account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"

    account = requests.get(
        account_url,
        headers={"X-Riot-Token": API_KEY}
    ).json()

    puuid = account["puuid"]

    # MATCH LIST
    match_ids = requests.get(
        f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10",
        headers={"X-Riot-Token": API_KEY}
    ).json()

    games = []

    total_k = 0
    total_d = 0
    total_a = 0
    wins = 0

    for match_id in match_ids:

        match = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
            headers={"X-Riot-Token": API_KEY}
        ).json()

        info = match["info"]

        participants = info["participants"]

        player_data = None

        for p in participants:
            if p["puuid"] == puuid:
                player_data = p
                break

        if not player_data:
            continue

        if player_data["win"]:
            wins += 1

        total_k += player_data["kills"]
        total_d += player_data["deaths"]
        total_a += player_data["assists"]

        items = [
            player_data["item0"],
            player_data["item1"],
            player_data["item2"],
            player_data["item3"],
            player_data["item4"],
            player_data["item5"]
        ]

        games.append({
            "champion": player_data["championName"],
            "kills": player_data["kills"],
            "deaths": player_data["deaths"],
            "assists": player_data["assists"],
            "win": player_data["win"],
            "items": items,
            "players": participants
        })

    games_count = len(games)

    avg_k = round(total_k/games_count,1)
    avg_d = round(total_d/games_count,1)
    avg_a = round(total_a/games_count,1)

    winrate = round((wins/games_count)*100)

    return render_template(
        "profile.html",
        name=player,
        games=games,
        avg_k=avg_k,
        avg_d=avg_d,
        avg_a=avg_a,
        winrate=winrate
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
