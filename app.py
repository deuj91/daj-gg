from flask import Flask, render_template, request, redirect
import requests
import os

app = Flask(__name__)

API_KEY = os.environ.get("RGAPI-17629850-7fb2-4282-ad49-3607656edeb0")

REGION = "europe"
PLATFORM = "euw1"

DD_VERSION = "14.1.1"

CACHE = {}

def cached_get(url):

    if url in CACHE:
        return CACHE[url]

    r = requests.get(url, timeout=5)

    if r.status_code != 200:
        return None

    data = r.json()

    CACHE[url] = data

    return data


def ai_analysis(player):

    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]
    cs = player["totalMinionsKilled"]
    vision = player["visionScore"]
    gold = player["goldEarned"]

    score = kills*3 + assists*2 - deaths

    if score > 25:
        return "🔥 MVP performance"

    if deaths > 10:
        return "⚠️ Too many deaths"

    if cs > 200:
        return "💰 Excellent farming"

    if vision > 35:
        return "👁️ Great vision control"

    if gold > 15000:
        return "💎 Strong economy"

    return "👍 Solid game"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player or "#" not in player:
        return redirect("/")

    name, tag = player.split("#")

    try:

        url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={API_KEY}"
        account = cached_get(url)

        if not account:
            return redirect("/")

        puuid = account["puuid"]

        url = f"https://{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={API_KEY}"
        summoner = cached_get(url)

        level = summoner["summonerLevel"]
        summoner_id = summoner["id"]

        url = f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={API_KEY}"
        rank_data = cached_get(url)

        rank = "Unranked"
        rank_icon = ""

        if rank_data and len(rank_data) > 0:

            tier = rank_data[0]["tier"]
            div = rank_data[0]["rank"]

            rank = f"{tier} {div}"

            rank_icon = f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{tier.lower()}.png"

        url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10&api_key={API_KEY}"
        match_ids = cached_get(url)

        games = []

        wins = 0
        total_k = total_d = total_a = total_cs = 0

        for match_id in match_ids:

            url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"
            match = cached_get(url)

            if not match:
                continue

            participants = match["info"]["participants"]

            player_data = None

            for p in participants:
                if p["puuid"] == puuid:
                    player_data = p
                    break

            if not player_data:
                continue

            if player_data["win"]:
                wins += 1

            kills = player_data["kills"]
            deaths = player_data["deaths"]
            assists = player_data["assists"]
            cs = player_data["totalMinionsKilled"]

            total_k += kills
            total_d += deaths
            total_a += assists
            total_cs += cs

            champion = player_data["championName"]

            analysis = ai_analysis(player_data)

            games.append({

                "champion": champion,

                "champion_img": f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{champion}.png",

                "kda": f"{kills}/{deaths}/{assists}",

                "cs": cs,

                "vision": player_data["visionScore"],

                "gold": player_data["goldEarned"],

                "result": "Victory" if player_data["win"] else "Defeat",

                "analysis": analysis
            })

        count = len(games)

        winrate = int((wins/count)*100) if count else 0

        avg_kda = f"{round(total_k/count,1)}/{round(total_d/count,1)}/{round(total_a/count,1)}" if count else "0/0/0"

        avg_cs = int(total_cs/count) if count else 0

        return render_template(

            "profile.html",

            player=player,
            level=level,
            rank=rank,
            rank_icon=rank_icon,
            games=games,
            winrate=winrate,
            avg_kda=avg_kda,
            avg_cs=avg_cs
        )

    except Exception as e:

        print("ERROR:", e)

        return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
