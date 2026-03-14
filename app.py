from flask import Flask, render_template, request, redirect
import requests
import os

app = Flask(__name__)

# récupération de la clé API depuis Render
API_KEY = os.environ.get("RGAPI-01a0c419-b7e4-4597-a53e-dc7d7e7efffd")

REGION = "europe"
PLATFORM = "euw1"
DD_VERSION = "14.1.1"


def riot_get(url):
    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            print("API ERROR:", r.text)
            return None

        return r.json()

    except Exception as e:
        print("REQUEST ERROR:", e)
        return None


def ai_coach(player):
    tips = []

    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]
    cs = player["totalMinionsKilled"]
    vision = player["visionScore"]

    kda = (kills + assists) / max(1, deaths)

    if deaths > 8:
        tips.append("Too many deaths, play safer.")

    if cs < 120:
        tips.append("Your farm is low, focus on CS.")

    if vision < 15:
        tips.append("Place more wards.")

    if kda > 4:
        tips.append("Great teamfight impact.")

    if not tips:
        tips.append("Solid performance.")

    return tips


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player:
        return redirect("/")

    if "#" not in player:
        return render_template("error.html", message="Use format: pseudo#tag")

    name, tag = player.split("#", 1)

    print("SEARCH:", player)
    print("API KEY:", API_KEY)

    if not API_KEY:
        return render_template("error.html", message="API key missing")

    # compte riot
    account_url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={API_KEY}"
    account = riot_get(account_url)

    if not account:
        return render_template("error.html", message="Player not found")

    puuid = account["puuid"]

    # summoner
    summoner_url = f"https://{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={API_KEY}"
    summoner = riot_get(summoner_url)

    if not summoner:
        return render_template("error.html", message="Summoner error")

    level = summoner["summonerLevel"]
    summoner_id = summoner["id"]

    # rank
    rank_url = f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={API_KEY}"
    ranks = riot_get(rank_url)

    rank = "Unranked"
    rank_icon = ""

    if ranks and len(ranks) > 0:
        tier = ranks[0]["tier"]
        div = ranks[0]["rank"]
        rank = f"{tier} {div}"

        rank_icon = f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{tier.lower()}.png"

    # matchs
    matches_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5&api_key={API_KEY}"
    match_ids = riot_get(matches_url)

    if not match_ids:
        return render_template("error.html", message="No matches found")

    games = []

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

        coach = ai_coach(player_data)

        games.append({

            "champion": player_data["championName"],

            "champion_img": f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{player_data['championName']}.png",

            "kda": f"{player_data['kills']}/{player_data['deaths']}/{player_data['assists']}",

            "cs": player_data["totalMinionsKilled"],

            "vision": player_data["visionScore"],

            "gold": player_data["goldEarned"],

            "result": "Victory" if player_data["win"] else "Defeat",

            "coach": coach

        })

    return render_template(

        "profile.html",

        player=player,
        level=level,
        rank=rank,
        rank_icon=rank_icon,
        games=games

    )


if __name__ == "__main__":
    app.run()
