from flask import Flask, render_template, request
import requests
import time
import os
import urllib.parse
from collections import Counter

app = Flask(__name__)

RIOT_API_KEY = os.getenv("RIOT_API_KEY")

CACHE = {}
CACHE_TIME = 300


def get_cache(key):
    if key in CACHE:
        value, timestamp = CACHE[key]
        if time.time() - timestamp < CACHE_TIME:
            return value
    return None


def set_cache(key, value):
    CACHE[key] = (value, time.time())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    try:

        player = request.args.get("player")

        if not player or "#" not in player:
            return "Use format Name#TAG"

        cached = get_cache(player)
        if cached:
            return cached

        name, tag = player.split("#")

        name = urllib.parse.quote(name)
        tag = urllib.parse.quote(tag)

        headers = {
            "X-Riot-Token": RIOT_API_KEY
        }

        acc_res = requests.get(
            f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
            headers=headers
        )

        acc = acc_res.json()

        if acc_res.status_code != 200:
            return f"Riot API Error {acc_res.status_code}: {acc}"

        if "puuid" not in acc:
            return f"Player not found"

        puuid = acc["puuid"]

        summoner = requests.get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}",
            headers=headers
        ).json()

        level = summoner["summonerLevel"]
        icon = summoner["profileIconId"]

        league = requests.get(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner['id']}",
            headers=headers
        ).json()

        rank = "Unranked"

        if league:
            tier = league[0]["tier"]
            div = league[0]["rank"]
            rank = f"{tier} {div}"

        tier = rank.split()[0].lower() if rank != "Unranked" else "unranked"

        rank_icon = f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{tier}.png"

        matches_id = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5",
            headers=headers
        ).json()

        matches = []
        champions = []

        for match_id in matches_id:

            data = requests.get(
                f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
                headers=headers
            ).json()

            info = data["info"]

            mode = info["gameMode"]

            blue = []
            red = []

            mvp_score = -999
            mvp = "Unknown"

            for p in info["participants"]:

                build = [
                    p["item0"],
                    p["item1"],
                    p["item2"],
                    p["item3"],
                    p["item4"],
                    p["item5"]
                ]

                player_data = {
                    "name": p.get("riotIdGameName", "Player"),
                    "champion": p["championName"],
                    "kills": p["kills"],
                    "deaths": p["deaths"],
                    "assists": p["assists"],
                    "gold": p["goldEarned"],
                    "build": build
                }

                score = p["kills"] + p["assists"] - p["deaths"]

                if score > mvp_score:
                    mvp_score = score
                    mvp = player_data["name"]

                if p["puuid"] == puuid:
                    champions.append(p["championName"])

                if p["teamId"] == 100:
                    blue.append(player_data)
                else:
                    red.append(player_data)

            matches.append({
                "blue": blue,
                "red": red,
                "mode": mode,
                "mvp": mvp
            })

        top_champs = Counter(champions).most_common(5)

        bg = champions[0] if champions else "Ahri"

        html = render_template(
            "profile.html",
            name=name,
            tag=tag,
            level=level,
            icon=icon,
            rank=rank,
            rank_icon=rank_icon,
            matches=matches,
            top_champs=top_champs,
            bg=bg
        )

        set_cache(player, html)

        return html

    except Exception as e:
        return f"Server error: {e}"


if __name__ == "__main__":
    app.run()
