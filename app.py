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

    try:

        player = request.args.get("player")

        if not player or "#" not in player:
            return "Use format name#tag"

        name, tag = player.split("#")

        # ACCOUNT
        account = requests.get(
            f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
            headers={"X-Riot-Token": API_KEY}
        ).json()

        puuid = account["puuid"]

        # SUMMONER
        summoner = requests.get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}",
            headers={"X-Riot-Token": API_KEY}
        ).json()

        summoner_id = summoner["id"]

        # RANK
        rank_data = requests.get(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}",
            headers={"X-Riot-Token": API_KEY}
        ).json()

        rank = "Unranked"

        if len(rank_data) > 0:

            r = rank_data[0]

            rank = f"{r['tier']} {r['rank']}"

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

            teams = {"allies": [], "enemies": []}

            player_team = player_data["teamId"]

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
                    teams["allies"].append(pdata)
                else:
                    teams["enemies"].append(pdata)

            games.append({
                "champion": player_data["championName"],
                "kills": player_data["kills"],
                "deaths": player_data["deaths"],
                "assists": player_data["assists"],
                "win": player_data["win"],
                "teams": teams
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
            winrate=winrate,
            rank=rank
        )

    except Exception as e:

        print("SERVER ERROR:", e)

        return f"Server error: {e}"


if __name__ == "__main__":
    app.run()
