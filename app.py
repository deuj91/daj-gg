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


def analyze_game(player):

    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]
    cs = player["totalMinionsKilled"]
    vision = player["visionScore"]

    score = kills*2 + assists - deaths

    if score > 20:
        return "MVP performance 🔥"

    if deaths > 10:
        return "Too many deaths ⚠️"

    if cs > 200:
        return "Great farming 💰"

    if vision > 30:
        return "Excellent vision 👁️"

    return "Average performance"


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

        url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5&api_key={API_KEY}"
        match_ids = cached_get(url)

        games = []

        wins = 0

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

            champion = player_data["championName"]

            analysis = analyze_game(player_data)

            games.append({

                "champion": champion,

                "champion_img": f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{champion}.png",

                "kda": f"{player_data['kills']}/{player_data['deaths']}/{player_data['assists']}",

                "cs": player_data["totalMinionsKilled"],

                "vision": player_data["visionScore"],

                "gold": player_data["goldEarned"],

                "result": "Victory" if player_data["win"] else "Defeat",

                "analysis": analysis
            })

        winrate = int((wins/len(games))*100) if games else 0

        return render_template(

            "profile.html",

            player=player,
            level=level,
            rank=rank,
            rank_icon=rank_icon,
            games=games,
            winrate=winrate

        )

    except Exception as e:

        print("ERROR:", e)

        return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
