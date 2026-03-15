from flask import Flask, render_template, request
import requests
import os
import time

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

# simple cache pour éviter trop d'appels API
cache = {}

def get_cache(key):
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < 120:
            return data
    return None

def set_cache(key, data):
    cache[key] = (data, time.time())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    try:

        player = request.args.get("player")

        if not player or "#" not in player:
            return "Invalid format. Use name#tag"

        name, tag = player.split("#")

        cache_key = f"{name}-{tag}"

        cached = get_cache(cache_key)

        if cached:
            return render_template(
                "profile.html",
                name=cached["name"],
                games=cached["games"],
                tips=cached["tips"]
            )

        # STEP 1 : get PUUID
        account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={API_KEY}"
        account = requests.get(account_url).json()

        if "puuid" not in account:
            return "Summoner not found"

        puuid = account["puuid"]

        # STEP 2 : match list
        matches_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5&api_key={API_KEY}"
        match_ids = requests.get(matches_url).json()

        games = []

        kills_total = 0
        deaths_total = 0

        for match_id in match_ids:

            match_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"
            match = requests.get(match_url).json()

            participants = match["metadata"]["participants"]
            info = match["info"]["participants"]

            player_index = participants.index(puuid)
            p = info[player_index]

            kills_total += p["kills"]
            deaths_total += p["deaths"]

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

        # AI COACH simple
        tips = []

        if deaths_total > kills_total:
            tips.append("You die too much. Play safer.")

        if kills_total < 10:
            tips.append("Try to be more aggressive in fights.")

        if not tips:
            tips.append("Good performance. Keep it up!")

        result = {
            "name": player,
            "games": games,
            "tips": tips
        }

        set_cache(cache_key, result)

        return render_template(
            "profile.html",
            name=player,
            games=games,
            tips=tips
        )

    except Exception as e:

        print("SERVER ERROR:", e)
        return "Server error. Check API key or logs."


if __name__ == "__main__":
    app.run(debug=True)
