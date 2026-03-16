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

        headers = {"X-Riot-Token": RIOT_API_KEY}

        # ACCOUNT API
        acc_res = requests.get(
            f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
            headers=headers
        )

        if acc_res.status_code != 200:
            return f"Account API error {acc_res.status_code}"

        acc = acc_res.json()

        puuid = acc.get("puuid")

        if not puuid:
            return "Player not found"

        # SUMMONER API
        summoner_res = requests.get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}",
            headers=headers
        )

        if summoner_res.status_code != 200:
            return f"Summoner API error {summoner_res.status_code}"

        summoner = summoner_res.json()

        summoner_id = summoner.get("id")

        if not summoner_id:
            return "Summoner ID not found"

        level = summoner.get("summonerLevel", 0)
        icon = summoner.get("profileIconId", 29)

        # RANK API
        league_res = requests.get(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}",
            headers=headers
        )

        league = league_res.json() if league_res.status_code == 200 else []

        rank = "Unranked"

        if league:
            tier = league[0]["tier"]
            div = league[0]["rank"]
            rank = f"{tier} {div}"

        tier = rank.split()[0].lower() if rank != "Unranked" else "unranked"

        rank_icon = f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{tier}.png"

        # MATCH LIST
        matches_id_res = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5",
            headers=headers
        )

        if matches_id_res.status_code != 200:
            return "Match history error"

        matches_id = matches_id_res.json()

        matches = []
        champions = []

        for match_id in matches_id:

            match_res = requests.get(
                f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
                headers=headers
            )

            if match_res.status_code != 200:
                continue

            data = match_res.json()
            info = data.get("info", {})

            blue = []
            red = []

            mvp_score = -999
            mvp = "Unknown"

            for p in info.get("participants", []):

                build = [
                    p.get("item0",0),
                    p.get("item1",0),
                    p.get("item2",0),
                    p.get("item3",0),
                    p.get("item4",0),
                    p.get("item5",0)
                ]

                player_data = {
                    "name": p.get("riotIdGameName","Player"),
                    "champion": p.get("championName",""),
                    "kills": p.get("kills",0),
                    "deaths": p.get("deaths",0),
                    "assists": p.get("assists",0),
                    "gold": p.get("goldEarned",0),
                    "build": build
                }

                score = player_data["kills"] + player_data["assists"] - player_data["deaths"]

                if score > mvp_score:
                    mvp_score = score
                    mvp = player_data["name"]

                if p.get("puuid") == puuid:
                    champions.append(p.get("championName",""))

                if p.get("teamId") == 100:
                    blue.append(player_data)
                else:
                    red.append(player_data)

            matches.append({
                "blue": blue,
                "red": red,
                "mode": info.get("gameMode",""),
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
