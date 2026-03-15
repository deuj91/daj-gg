from flask import Flask, render_template, request
import requests
import os
import time

app = Flask(__name__)

API_KEY = os.environ.get("RIOT_API_KEY")

REGION_ACCOUNT = "https://europe.api.riotgames.com"
REGION_MATCH = "https://europe.api.riotgames.com"

session = requests.Session()

CACHE = {}
CACHE_TIME = 300


def ai_coach(games):

    if not games:
        return ["No matches found."]

    kills = sum(g["kills"] for g in games)
    deaths = sum(g["deaths"] for g in games)
    assists = sum(g["assists"] for g in games)

    kda = (kills + assists) / max(1, deaths)

    tips = []

    if deaths / len(games) > 7:
        tips.append("Try dying less and improve positioning.")

    if kills / len(games) < 4:
        tips.append("Try increasing your kill participation.")

    if kda > 4:
        tips.append("Excellent KDA, keep it up!")

    if not tips:
        tips.append("Balanced performance overall.")

    return tips


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player:
        return render_template("error.html", message="Enter Riot ID (example: Caps#EUW)")

    if "#" not in player:
        return render_template("error.html", message="Format must be Name#TAG")

    # cache
    if player in CACHE:

        data, timestamp = CACHE[player]

        if time.time() - timestamp < CACHE_TIME:
            return render_template(
                "profile.html",
                name=player,
                games=data["games"],
                tips=data["tips"]
            )

    try:

        name, tag = player.split("#")

        # account
        account_url = f"{REGION_ACCOUNT}/riot/account/v1/accounts/by-riot-id/{name}/{tag}"

        acc_response = session.get(
            account_url,
            headers={"X-Riot-Token": API_KEY}
        )

        if acc_response.status_code != 200:
            return render_template("error.html", message="Player not found")

        account = acc_response.json()

        puuid = account.get("puuid")

        if not puuid:
            return render_template("error.html", message="PUUID not found")

        # match list
        matches_url = f"{REGION_MATCH}/lol/match/v5/matches/by-puuid/{puuid}/ids?count=10"

        matches_response = session.get(
            matches_url,
            headers={"X-Riot-Token": API_KEY}
        )

        if matches_response.status_code != 200:
            return render_template("error.html", message="Unable to fetch matches")

        match_ids = matches_response.json()

        games = []

        for match_id in match_ids:

            match_url = f"{REGION_MATCH}/lol/match/v5/matches/{match_id}"

            match_response = session.get(
                match_url,
                headers={"X-Riot-Token": API_KEY}
            )

            if match_response.status_code != 200:
                continue

            match_data = match_response.json()

            info = match_data["info"]["participants"]

            players = []

            for p in info:

                players.append({
                    "name": p.get("riotIdGameName", "Unknown"),
                    "champion": p.get("championName", "Unknown"),
                    "items": [
                        p.get("item0", 0),
                        p.get("item1", 0),
                        p.get("item2", 0),
                        p.get("item3", 0),
                        p.get("item4", 0),
                        p.get("item5", 0)
                    ]
                })

            me = next((p for p in info if p["puuid"] == puuid), None)

            if not me:
                continue

            games.append({
                "champion": me.get("championName", "Unknown"),
                "kills": me.get("kills", 0),
                "deaths": me.get("deaths", 0),
                "assists": me.get("assists", 0),
                "win": me.get("win", False),
                "players": players
            })

        tips = ai_coach(games)

        CACHE[player] = (
            {"games": games, "tips": tips},
            time.time()
        )

        return render_template(
            "profile.html",
            name=player,
            games=games,
            tips=tips
        )

    except Exception as e:

        print("SERVER ERROR:", e)

        return render_template(
            "error.html",
            message="Server error. Check logs."
        )


if __name__ == "__main__":
    app.run()
