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
            return "Use format: name#tag"

        name, tag = player.split("#")

        # ACCOUNT REQUEST
        account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"

        account_res = requests.get(
            account_url,
            headers={"X-Riot-Token": API_KEY}
        )

        account = account_res.json()

        if "puuid" not in account:
            return "Summoner not found"

        puuid = account["puuid"]

        # MATCH LIST
        matchlist_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"

        matchlist_res = requests.get(
            matchlist_url,
            headers={"X-Riot-Token": API_KEY}
        )

        match_ids = matchlist_res.json()

        games = []

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

            items = [
                player_data.get("item0", 0),
                player_data.get("item1", 0),
                player_data.get("item2", 0),
                player_data.get("item3", 0),
                player_data.get("item4", 0),
                player_data.get("item5", 0)
            ]

            players = []

            for p in participants:
                players.append({
                    "name": p.get("summonerName"),
                    "champion": p.get("championName")
                })

            games.append({
                "champion": player_data.get("championName"),
                "kills": player_data.get("kills"),
                "deaths": player_data.get("deaths"),
                "assists": player_data.get("assists"),
                "win": player_data.get("win"),
                "items": items,
                "players": players
            })

        tips = [
            "Try to reduce early deaths",
            "Improve vision control with more wards"
        ]

        return render_template(
            "profile.html",
            name=player,
            games=games,
            tips=tips
        )

    except Exception as e:

        print("SERVER ERROR:", e)
        return f"Server error: {e}"


if __name__ == "__main__":
    app.run()
