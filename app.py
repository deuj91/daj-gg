from flask import Flask, render_template, request
import requests
import os

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    try:

        player = request.args.get("player")

        if not player or "#" not in player:
            return "Use format: name#tag"

        name, tag = player.split("#")

        # GET ACCOUNT
        url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={API_KEY}"
        account = requests.get(url).json()

        if "puuid" not in account:
            return "Summoner not found"

        puuid = account["puuid"]

        # MATCH LIST
        matches_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5&api_key={API_KEY}"
        match_ids = requests.get(matches_url).json()

        games = []

        for match_id in match_ids:

            match_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"
            match = requests.get(match_url).json()

            info = match["info"]["participants"]
            metadata = match["metadata"]["participants"]

            player_index = metadata.index(puuid)
            p = info[player_index]

            items = [
                p["item0"],
                p["item1"],
                p["item2"],
                p["item3"],
                p["item4"],
                p["item5"]
            ]

            players = []

            for pl in info:
                players.append({
                    "name": pl["summonerName"],
                    "champion": pl["championName"]
                })

            games.append({

                "champion": p["championName"],
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
                "win": p["win"],
                "items": items,
                "players": players

            })

        tips = ["Focus on map awareness", "Try to reduce deaths"]

        return render_template(
            "profile.html",
            name=player,
            games=games,
            tips=tips
        )

    except Exception as e:
    import traceback
    traceback.print_exc()
    return f"SERVER ERROR: {e}"


if __name__ == "__main__":
    app.run()
