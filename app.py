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
        account = requests.get(
            f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
            headers={"X-Riot-Token": API_KEY}
        ).json()

        if "puuid" not in account:
            return f"Player not found: {account}"

        puuid = account["puuid"]

        # SUMMONER
        summoner = requests.get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}",
            headers={"X-Riot-Token": API_KEY}
        ).json()

        if "id" not in summoner:
            return f"Summoner data error: {summoner}"

        icon = summoner.get("profileIconId", 29)
        level = summoner.get("summonerLevel", 0)
        summoner_id = summoner["id"]

        # RANK
        rank_data = requests.get(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}",
            headers={"X-Riot-Token": API_KEY}
        ).json()

        rank = "Unranked"

        if isinstance(rank_data, list):
            for q in rank_data:
                if q["queueType"] == "RANKED_SOLO_5x5":
                    rank = f'{q["tier"]} {q["rank"]}'
                    break

        # MATCHLIST
        match_ids = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5",
            headers={"X-Riot-Token": API_KEY}
        ).json()

        games = []

        total_k = total_d = total_a = wins = 0

        for match_id in match_ids:

            match = requests.get(
                f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
                headers={"X-Riot-Token": API_KEY}
            ).json()

            info = match.get("info", {})

            duration = int(info.get("gameDuration", 0) / 60)

            participants = info.get("participants", [])

            player_data = next((p for p in participants if p["puuid"] == puuid), None)

            if not player_data:
                continue

            if player_data["win"]:
                wins += 1

            total_k += player_data["kills"]
            total_d += player_data["deaths"]
            total_a += player_data["assists"]

            team_id = player_data["teamId"]

            allies = []
            enemies = []

            for p in participants:

                build = [
                    p["item0"],
                    p["item1"],
                    p["item2"],
                    p["item3"],
                    p["item4"],
                    p["item5"]
                ]

                build = [i for i in build if i != 0]

                pdata = {
                    "name": p["summonerName"],
                    "champion": p["championName"],
                    "kills": p["kills"],
                    "deaths": p["deaths"],
                    "assists": p["assists"],
                    "build": build
                }

                if p["teamId"] == team_id:
                    allies.append(pdata)
                else:
                    enemies.append(pdata)

            games.append({
                "champion": player_data["championName"],
                "kills": player_data["kills"],
                "deaths": player_data["deaths"],
                "assists": player_data["assists"],
                "win": player_data["win"],
                "duration": duration,
                "allies": allies,
                "enemies": enemies
            })

        if len(games) == 0:
            return "No matches found"

        avg_k = round(total_k / len(games), 1)
        avg_d = round(total_d / len(games), 1)
        avg_a = round(total_a / len(games), 1)

        winrate = round((wins / len(games)) * 100)

        return render_template(
            "profile.html",
            name=player,
            icon=icon,
            level=level,
            rank=rank,
            games=games,
            avg_k=avg_k,
            avg_d=avg_d,
            avg_a=avg_a,
            winrate=winrate
        )

    except Exception as e:

        print("SERVER ERROR:", e)

        return f"Server error: {e}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
