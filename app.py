from flask import Flask, render_template, request
import requests
import os
import time

app = Flask(__name__)

API_KEY = os.environ.get("RIOT_API_KEY")

MATCH_REGION = "europe"

CACHE = {}
CACHE_TIME = 300

session = requests.Session()


def ai_coach(games):

    if not games:
        return ["No matches found."]

    kills = sum(g["kills"] for g in games)
    deaths = sum(g["deaths"] for g in games)
    assists = sum(g["assists"] for g in games)

    kda = (kills + assists) / max(1, deaths)

    tips = []

    if deaths/len(games) > 7:
        tips.append("You die too much. Try safer positioning.")

    if kills/len(games) < 4:
        tips.append("Your damage seems low. Try more aggressive plays.")

    if kda > 4:
        tips.append("Excellent KDA. Keep it up.")

    if not tips:
        tips.append("Solid performance overall.")

    return tips


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player:
        return "Enter a Riot ID (Name#Tag)"

    if player in CACHE:

        data, t = CACHE[player]

        if time.time() - t < CACHE_TIME:

            return render_template(
                "profile.html",
                name=player,
                games=data["games"],
                tips=data["tips"]
            )

    try:

        name, tag = player.split("#")

        acc_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"

        acc = session.get(
            acc_url,
            headers={"X-Riot-Token": API_KEY}
        ).json()

        if "puuid" not in acc:
            return "Summoner not found"

        puuid = acc["puuid"]

        matches_url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=10"

        match_ids = session.get(
            matches_url,
            headers={"X-Riot-Token": API_KEY}
        ).json()

        games = []

        for match_id in match_ids:

            murl = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"

            match = session.get(
                murl,
                headers={"X-Riot-Token": API_KEY}
            ).json()

            info = match["info"]["participants"]

            players = []

            for p in info:

                players.append({

                    "name": p.get("riotIdGameName","Unknown"),
                    "champion": p.get("championName","Unknown"),
                    "items":[
                        p.get("item0",0),
                        p.get("item1",0),
                        p.get("item2",0),
                        p.get("item3",0),
                        p.get("item4",0),
                        p.get("item5",0)
                    ]

                })

            me = next((p for p in info if p["puuid"] == puuid), None)

            if not me:
                continue

            games.append({

                "champion": me["championName"],
                "kills": me["kills"],
                "deaths": me["deaths"],
                "assists": me["assists"],
                "win": me["win"],
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

        print("ERROR:", e)

        return "Server error (check logs)"


if __name__ == "__main__":
    app.run()
