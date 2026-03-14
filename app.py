from flask import Flask, render_template, request
import requests
import os
import time

app = Flask(__name__)

API_KEY = os.environ.get("RGAPI-17629850-7fb2-4282-ad49-3607656edeb0")

REGION = "europe"
PLATFORM = "euw1"

CACHE = {}

version = requests.get(
"https://ddragon.leagueoflegends.com/api/versions.json"
).json()[0]


def cached_request(url):

    if url in CACHE and time.time() - CACHE[url]["time"] < 60:
        return CACHE[url]["data"]

    r = requests.get(url, headers={"X-Riot-Token": API_KEY})

    data = r.json()

    CACHE[url] = {
        "data": data,
        "time": time.time()
    }

    return data


def player_score(player):

    score = 0

    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]

    cs = player["totalMinionsKilled"] + player["neutralMinionsKilled"]
    vision = player["visionScore"]
    damage = player["totalDamageDealtToChampions"]

    kda = (kills + assists) / max(1, deaths)

    score += min(kda * 10, 40)
    score += min(cs / 10, 20)
    score += min(vision, 20)
    score += min(damage / 2000, 20)

    return int(score)


def win_probability(player):

    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]

    cs = player["totalMinionsKilled"] + player["neutralMinionsKilled"]
    gold = player["goldEarned"]
    damage = player["totalDamageDealtToChampions"]

    score = 0

    score += (kills + assists) * 2
    score -= deaths * 2

    score += cs / 10
    score += gold / 1000
    score += damage / 5000

    probability = min(max(int(score), 0), 100)

    return probability


def detect_feeder(team):

    worst = None
    worst_score = 999

    for p in team:

        deaths = p["deaths"]
        kda = (p["kills"] + p["assists"]) / max(1, deaths)

        score = kda - deaths

        if score < worst_score:
            worst_score = score
            worst = p

    if worst:

        name = worst.get("riotIdGameName", "Unknown")
        champ = worst["championName"]

        return f"⚠️ Game difficile à cause de {name} ({champ})"

    return ""


def analyze_game(player, team):

    analysis = []

    kda = (player["kills"] + player["assists"]) / max(1, player["deaths"])
    cs = player["totalMinionsKilled"] + player["neutralMinionsKilled"]
    vision = player["visionScore"]
    damage = player["totalDamageDealtToChampions"]

    if kda > 4:
        analysis.append("🔥 Excellent KDA")

    if cs > 200:
        analysis.append("🌾 Farm très bon")

    if vision > 30:
        analysis.append("👁 Bonne vision")

    if damage > 25000:
        analysis.append("💥 Gros dégâts")

    if player["kills"] > 10:
        analysis.append("⭐ Carry potentiel")

    if len(analysis) >= 4:
        result = "🟢 Game gagnable"

    elif len(analysis) >= 2:
        result = "🟡 Game difficile"

    else:
        result = "🔴 Game très difficile"

    return result, analysis


def get_player(puuid, match):

    for p in match["info"]["participants"]:
        if p["puuid"] == puuid:
            return p

    return None


def fetch_match(match_id, puuid):

    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"

    match = cached_request(url)

    if "info" not in match:
        return None

    player = get_player(puuid, match)

    if not player:
        return None

    champion = player["championName"]

    champion_img = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champion}.png"

    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]

    cs = player["totalMinionsKilled"] + player["neutralMinionsKilled"]
    gold = player["goldEarned"]
    vision = player["visionScore"]

    result = "Victory" if player["win"] else "Defeat"

    items_list = []

    for i in range(7):

        item = player[f"item{i}"]

        if item != 0:

            items_list.append(
                f"https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item}.png"
            )

    team = []

    allies = []

    team_id = player["teamId"]

    for p in match["info"]["participants"]:

        if p["teamId"] == team_id:
            team.append(p)

        if p["teamId"] == team_id and p["puuid"] != puuid:

            ally_items = []

            for i in range(7):

                item = p[f"item{i}"]

                if item != 0:

                    ally_items.append(
                        f"https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item}.png"
                    )

            allies.append({

                "name": p.get("riotIdGameName", "Unknown"),

                "champion": p["championName"],

                "champion_img": f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{p['championName']}.png",

                "kda": f"{p['kills']}/{p['deaths']}/{p['assists']}",

                "items_list": ally_items

            })

    ai_result, ai_details = analyze_game(player, team)

    score = player_score(player)

    prob = win_probability(player)

    feeder = detect_feeder(team)

    return {

        "champion": champion,
        "champion_img": champion_img,

        "kda": f"{kills}/{deaths}/{assists}",

        "cs": cs,
        "gold": gold,
        "vision": vision,

        "result": result,

        "items_list": items_list,

        "allies": allies,

        "analysis": ai_result,
        "analysis_details": ai_details,

        "score": score,
        "win_probability": prob,
        "feeder": feeder

    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player or "#" not in player:
        return render_template("index.html")

    name, tag = player.split("#")

    account_url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"

    account = cached_request(account_url)

    if "puuid" not in account:
        return render_template("index.html")

    puuid = account["puuid"]

    matches_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=10"

    match_ids = cached_request(matches_url)

    games = []

    for match_id in match_ids:

        g = fetch_match(match_id, puuid)

        if g:
            games.append(g)

    return render_template(
        "index.html",
        games=games,
        player=player
    )


if __name__ == "__main__":
    app.run(debug=True)