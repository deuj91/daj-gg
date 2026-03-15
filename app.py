from flask import Flask, render_template, request
import requests
import os
from urllib.parse import quote

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def search():
    try:
        player = request.args.get("player")

        if not player or "#" not in player:
            return "Use format: name#tag"

        name, tag = player.split("#")

        name = quote(name)
        tag = quote(tag)

        # ACCOUNT
        account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"

        account_res = requests.get(
            account_url,
            headers={"X-Riot-Token": API_KEY}
        )

        if account_res.status_code != 200:
            return f"Riot API error {account_res.status_code}"

        account = account_res.json()

        if "puuid" not in account:
            return "Player not found"

        puuid = account["puuid"]

        # MATCH LIST
        matchlist_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"

        matchlist_res = requests.get(
            matchlist_url,
            headers={"X-Riot-Token": API_KEY}
        )

        match_ids = matchlist_res.json()

        games = []

        total_k = 0
        total_d = 0
        total_a = 0
        wins = 0

        for match_id in match_ids:

            match_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}"

            match_res = requests.get(
                match_url,
                headers={"X-Riot-Token": API_KEY}
            )

            match = match_res.json()

            info = match.get("info")

            if not info:
                continue

            participants = info.get("participants", [])

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

            player_team = player_data["teamId"]

            allies = []
            enemies = []

            for p in participants:

                pdata = {
                    "name": p["summonerName"],
                    "champion": p["championName"],
                    "kills": p["kills"],
                    "deaths": p["deaths"],
                    "assists": p["assists"],
                    "items": [
                        p["item0"],
                        p["item1"],
                        p["item2"],
                        p["item3"],
                        p["item4"],
                        p["item5"]
                    ]
                }

                if p["teamId"] == player_team:
                    allies.append(pdata)
                else:
                    enemies.append(pdata)

            games.append({
                "champion": player_data["championName"],
                "kills": player_data["kills"],
                "deaths": player_data["deaths"],
                "assists": player_data["assists"],
                "win": player_data["win"],
                "allies": allies,
                "enemies": enemies
            })

        if len(games) == 0:
            avg_k = avg_d = avg_a = 0
            winrate = 0
        else:
            avg_k = round(total_k / len(games), 1)
            avg_d = round(total_d / len(games), 1)
            avg_a = round(total_a / len(games), 1)
            winrate = round((wins / len(games)) * 100)

        rank = "Unranked"

        return render_template(
            "profile.html",
            name=player,
            games=games,
            avg_k=avg_k,
            avg_d=avg_d,
            avg_a=avg_a,
            winrate=winrate,
            rank=rank
        )

    except Exception as e:
        print("SERVER ERROR:", e)
        return f"Server error: {e}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
