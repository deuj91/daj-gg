from flask import Flask, render_template, request
import requests
import os
import time

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

CACHE = {}
CACHE_TIME = 120

VERSION = "14.6.1"
DDRAGON = f"https://ddragon.leagueoflegends.com/cdn/{VERSION}"

headers = {"X-Riot-Token": API_KEY}


def get_cache(key):
    if key in CACHE:
        data, timestamp = CACHE[key]
        if time.time() - timestamp < CACHE_TIME:
            return data
    return None


def set_cache(key, value):
    CACHE[key] = (value, time.time())


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def search():

    try:

        player = request.args.get("player")

        if not player or "#" not in player:
            return "Use format: name#tag"

        cached = get_cache(player)
        if cached:
            return cached

        name, tag = player.split("#")

        # ACCOUNT
        account = requests.get(
            f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
            headers=headers,
            timeout=10
        ).json()

        puuid = account["puuid"]

        # SUMMONER
        summoner = requests.get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}",
            headers=headers,
            timeout=10
        ).json()

        icon = summoner["profileIconId"]
        level = summoner["summonerLevel"]

        # RANK
        rank = "Unranked"

        leagues = requests.get(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}",
            headers=headers,
            timeout=10
        ).json()

        for r in leagues:
            if r["queueType"] == "RANKED_SOLO_5x5":
                rank = f'{r["tier"]} {r["rank"]} {r["leaguePoints"]}LP'

        # MATCHES
        match_ids = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5",
            headers=headers,
            timeout=10
        ).json()

        matches = []

        wins = 0
        total_k = total_d = total_a = 0
        total_cs = 0

        for match_id in match_ids:

            match = requests.get(
                f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
                headers=headers,
                timeout=10
            ).json()

            info = match["info"]
            participants = info["participants"]

            player_data = next(p for p in participants if p["puuid"] == puuid)

            if player_data["win"]:
                wins += 1

            total_k += player_data["kills"]
            total_d += player_data["deaths"]
            total_a += player_data["assists"]
            total_cs += player_data["totalMinionsKilled"]

            build = [
                player_data["item0"],
                player_data["item1"],
                player_data["item2"],
                player_data["item3"],
                player_data["item4"],
                player_data["item5"]
            ]

            matches.append({
                "champion": player_data["championName"],
                "kills": player_data["kills"],
                "deaths": player_data["deaths"],
                "assists": player_data["assists"],
                "build": build,
                "cs": player_data["totalMinionsKilled"],
                "damage": player_data["totalDamageDealtToChampions"],
                "gold": player_data["goldEarned"],
                "win": player_data["win"],
                "duration": int(info["gameDuration"]/60)
            })

        games = len(match_ids)

        kda = f"{total_k/games:.1f}/{total_d/games:.1f}/{total_a/games:.1f}"
        winrate = int((wins/games)*100)
        cs_avg = int(total_cs/games)

        bg = matches[0]["champion"]

        html = render_template(
            "profile.html",
            name=player,
            icon=icon,
            level=level,
            rank=rank,
            matches=matches,
            kda=kda,
            winrate=winrate,
            cs_avg=cs_avg,
            bg=bg
        )

        set_cache(player, html)

        return html

    except Exception as e:

        return f"Server error: {str(e)}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
