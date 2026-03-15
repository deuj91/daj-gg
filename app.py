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

        account = requests.get(
            account_url,
            headers={"X-Riot-Token": API_KEY}
        ).json()

        if "puuid" not in account:
            return "Summoner not found"

        puuid = account["puuid"]

        # MATCH LIST
        matchlist_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"

        match_ids = requests.get(
            matchlist_url,
            headers={"X-Riot-Token": API_KEY}
        ).json()

        games = []

        for match_id in match_ids:

            match_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}"

            match = requests.get(
                match_url,
                headers={"X-Riot-Token": API_KEY}
            ).json()

            participants = match["info"]["participants"]

            player_data = None

            for p in participants:
                if p["puuid"] == puuid:
                    player_data = p

            if not player_data:
                continue

            items = [
                player_data["item0"],
                player_data["item1"],
                player_data["item2"],
                player_data["item3"],
                player_data["item4"],
                player_data["item5"]
            ]

            players = []

            for p in participants:
                players.append({
                    "name": p["summonerName"],
                    "champion": p["championName"]
                })

            games.append({
                "champion": player_data["championName"],
                "kills": player_data["kills"],
                "deaths": player_data["deaths"],
                "assists": player_data["assists"],
                "win": player_data["win"],
                "items": items,
                "players": players
            })

        tips = [
            "Reduce deaths to improve consistency",
            "Track enemy jungler more often"
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
