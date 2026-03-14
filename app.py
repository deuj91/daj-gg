from flask import Flask, render_template, request, redirect
import requests

app = Flask(__name__)

API_KEY = "RGAPI-17629850-7fb2-4282-ad49-3607656edeb0"

REGION = "europe"
MATCH_REGION = "europe"

def get_rank_icon(tier):
    tier = tier.lower()
    return f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{tier}.png"


@app.route("/")
def index():
    return render_template("index.html", games=None)


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player or "#" not in player:
        return redirect("/")

    name, tag = player.split("#")

    # 1️⃣ récupérer le PUUID
    url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={API_KEY}"
    r = requests.get(url)

    if r.status_code != 200:
        return render_template("index.html", games=None)

    data = r.json()
    puuid = data["puuid"]

    # 2️⃣ récupérer summoner id
    url = f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={API_KEY}"
    r = requests.get(url)

    if r.status_code != 200:
        return render_template("index.html", games=None)

    summoner = r.json()
    summoner_id = summoner["id"]

    # 3️⃣ récupérer rank
    url = f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={API_KEY}"
    r = requests.get(url)

    rank = "Unranked"
    rank_icon = ""

    if r.status_code == 200 and len(r.json()) > 0:
        ranked = r.json()[0]
        tier = ranked["tier"]
        rank_div = ranked["rank"]

        rank = f"{tier} {rank_div}"
        rank_icon = get_rank_icon(tier)

    # 4️⃣ récupérer matchs
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5&api_key={API_KEY}"
    r = requests.get(url)

    if r.status_code != 200:
        return render_template("index.html", games=None)

    match_ids = r.json()

    games = []

    for match_id in match_ids:

        url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"
        r = requests.get(url)

        if r.status_code != 200:
            continue

        match = r.json()

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

        k = player_data["kills"]
        d = player_data["deaths"]
        a = player_data["assists"]

        kda = f"{k}/{d}/{a}"

        cs = player_data["totalMinionsKilled"]

        gold = player_data["goldEarned"]

        vision = player_data["visionScore"]

        result = "Victory" if player_data["win"] else "Defeat"

        champion_img = f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/{champion}.png"

        items = []

        for i in range(7):
            item_id = player_data[f"item{i}"]
            if item_id != 0:
                items.append(
                    f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/item/{item_id}.png"
                )

        allies = []

        team_id = player_data["teamId"]

        for p in participants:

            if p["teamId"] != team_id or p["puuid"] == puuid:
                continue

            ally_items = []

            for i in range(7):
                item_id = p[f"item{i}"]
                if item_id != 0:
                    ally_items.append(
                        f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/item/{item_id}.png"
                    )

            allies.append({
                "name": p["riotIdGameName"],
                "champion": p["championName"],
                "champion_img": f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/{p['championName']}.png",
                "kda": f"{p['kills']}/{p['deaths']}/{p['assists']}",
                "items_list": ally_items
            })

        # petite analyse simple
        analysis = "Game difficile"

        if cs > 180:
            analysis = "Très bon farm"

        if k > 10:
            analysis = "Très bonne performance"

        games.append({
            "champion_img": champion_img,
            "kda": kda,
            "cs": cs,
            "gold": gold,
            "vision": vision,
            "result": result,
            "items_list": items,
            "analysis": analysis,
            "analysis_details": [
                f"Kills: {k}",
                f"CS: {cs}",
                f"Vision: {vision}"
            ],
            "allies": allies
        })

    return render_template(
        "index.html",
        games=games,
        player=player,
        rank=rank,
        rank_icon=rank_icon
    )


if __name__ == "__main__":
    app.run(debug=True)
    )


if __name__ == "__main__":
    app.run(debug=True)


if __name__ == "__main__":
    app.run(debug=True)
