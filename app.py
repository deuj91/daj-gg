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

    score = player["kills"]*2 + player["assists"] - player["deaths"]

    if score > 15:
        return "MVP performance 🔥"

    if player["deaths"] > 10:
        return "Feeding too much ⚠️"

    if player["visionScore"] > 30:
        return "Excellent vision control 👁️"

    if player["totalMinionsKilled"] > 200:
        return "Great farming 💰"

    return "Average game"


@app.route("/")
def index():
    return render_template("index.html", games=None)


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player or "#" not in player:
        return redirect("/")

    name, tag = player.split("#")

    try:

        # ACCOUNT
        url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={API_KEY}"
        account = cached_get(url)

        if not account:
            return render_template("index.html", games=[])

        puuid = account["puuid"]

        # SUMMONER
        url = f"https://{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={API_KEY}"
        summoner = cached_get(url)

        if not summoner:
            return render_template("index.html", games=[])

        summoner_id = summoner["id"]

        # RANK
        rank = "Unranked"
        rank_icon = ""

        url = f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={API_KEY}"
        rank_data = cached_get(url)

        if rank_data and len(rank_data) > 0:

            tier = rank_data[0]["tier"]
            div = rank_data[0]["rank"]

            rank = f"{tier} {div}"

            rank_icon = f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{tier.lower()}.png"

        # MATCH LIST
        url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=3&api_key={API_KEY}"
        match_ids = cached_get(url)

        if not match_ids:
            return render_template("index.html", games=[])

        games = []

        for match_id in match_ids:

            url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"
            match = cached_get(url)

            if not match:
                continue

            info = match["info"]

            participants = info["participants"]

            player_data = None

            for p in participants:
                if p["puuid"] == puuid:
                    player_data = p
                    break

            if not player_data:
                continue

            champion = player_data["championName"]

            result = "Victory" if player_data["win"] else "Defeat"

            analysis = analyze_game(player_data)

            champion_img = f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{champion}.png"

            items = []

            for i in range(7):

                item = player_data[f"item{i}"]

                if item != 0:

                    items.append(
                        f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/item/{item}.png"
                    )

            games.append({

                "champion_img": champion_img,
                "kda": f"{player_data['kills']}/{player_data['deaths']}/{player_data['assists']}",
                "cs": player_data["totalMinionsKilled"],
                "vision": player_data["visionScore"],
                "gold": player_data["goldEarned"],
                "result": result,
                "analysis": analysis,
                "items": items
            })

        return render_template(
            "index.html",
            player=player,
            rank=rank,
            rank_icon=rank_icon,
            games=games
        )

    except Exception as e:

        print("ERROR:", e)

        return render_template("index.html", games=[])
        

if __name__ == "__main__":
    app.run(debug=True)
