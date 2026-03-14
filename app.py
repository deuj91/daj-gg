from flask import Flask, render_template, request, redirect
import requests
import os
from flask_caching import Cache

app = Flask(__name__)

cache = Cache(config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300
})

cache.init_app(app)

API_KEY = os.environ.get("RGAPI-17629850-7fb2-4282-ad49-3607656edeb0")

REGION = "europe"
PLATFORM = "euw1"
DD_VERSION = "14.1.1"


def riot_get(url):

    try:

        r = requests.get(url, timeout=6)

        if r.status_code != 200:
            print("API ERROR:", r.text)
            return None

        return r.json()

    except Exception as e:

        print("REQUEST ERROR:", e)
        return None


def detect_mvp(participants):

    best_score = -999
    worst_score = 999

    mvp = None
    feeder = None

    for p in participants:

        score = p["kills"]*3 + p["assists"]*2 - p["deaths"]

        name = p.get("riotIdGameName") or p.get("summonerName")

        if score > best_score:
            best_score = score
            mvp = name

        if score < worst_score:
            worst_score = score
            feeder = name

    return mvp, feeder


def ai_coach(player, match):

    tips = []

    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]

    cs = player["totalMinionsKilled"]
    vision = player["visionScore"]

    duration = match["info"]["gameDuration"] / 60

    cs_min = cs / duration

    kda = (kills + assists) / max(1, deaths)

    if deaths > 8:
        tips.append("⚠️ Too many deaths. Try safer positioning.")

    if cs_min < 6:
        tips.append("💰 Your CS/min is low.")

    if cs_min > 8:
        tips.append("🔥 Excellent farming.")

    if vision < 20:
        tips.append("👁️ Place more wards.")

    if kda > 4:
        tips.append("🏆 Great teamfight impact.")

    if not tips:
        tips.append("👍 Solid performance.")

    return tips


@app.route("/")
def index():

    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player:
        return redirect("/")

    try:
        name, tag = player.split("#", 1)
    except:
        return render_template("error.html", message="Format: pseudo#tag")

    print("SEARCH:", player)

    account_url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={API_KEY}"
    account = riot_get(account_url)

    if not account:
        return render_template("error.html", message="Player not found")

    puuid = account["puuid"]

    summoner_url = f"https://{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={API_KEY}"
    summoner = riot_get(summoner_url)

    if not summoner:
        return render_template("error.html", message="Summoner error")

    level = summoner["summonerLevel"]
    summoner_id = summoner["id"]

    rank_url = f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={API_KEY}"
    ranks = riot_get(rank_url)

    rank = "Unranked"
    rank_icon = ""

    if ranks and len(ranks) > 0:

        tier = ranks[0]["tier"]
        div = ranks[0]["rank"]

        rank = f"{tier} {div}"

        rank_icon = f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{tier.lower()}.png"

    matches_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5&api_key={API_KEY}"
    match_ids = riot_get(matches_url)

    if not match_ids:
        return render_template("error.html", message="No matches found")

    games = []

    wins = 0
    total_k = total_d = total_a = total_cs = 0

    for match_id in match_ids:

        match_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"
        match = riot_get(match_url)

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

        kills = player_data["kills"]
        deaths = player_data["deaths"]
        assists = player_data["assists"]
        cs = player_data["totalMinionsKilled"]

        if player_data["win"]:
            wins += 1

        total_k += kills
        total_d += deaths
        total_a += assists
        total_cs += cs

        team_kills = sum(
            p["kills"] for p in participants
            if p["teamId"] == player_data["teamId"]
        )

        kp = int(((kills + assists) / max(1, team_kills)) * 100)

        mvp, feeder = detect_mvp(participants)

        coach = ai_coach(player_data, match)

        games.append({

            "champion": player_data["championName"],

            "champion_img": f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{player_data['championName']}.png",

            "kda": f"{kills}/{deaths}/{assists}",

            "cs": cs,

            "vision": player_data["visionScore"],

            "gold": player_data["goldEarned"],

            "kp": kp,

            "result": "Victory" if player_data["win"] else "Defeat",

            "mvp": mvp,

            "feeder": feeder,

            "coach": coach

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


if __name__ == "__main__":
    app.run()
