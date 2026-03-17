import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

REGION = "euw1"
MATCH_REGION = "europe"

SUMMONER_URL = f"https://{REGION}.api.riotgames.com"
MATCH_URL = f"https://{MATCH_REGION}.api.riotgames.com"
LEAGUE_URL = f"https://{REGION}.api.riotgames.com"


def riot(url):
    headers = {"X-Riot-Token": API_KEY}
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print("RIOT ERROR:", r.text)
        return None

    return r.json()


def analyse(p):

    kills = p["kills"]
    deaths = p["deaths"]
    assists = p["assists"]
    gold = p["goldEarned"]
    vision = p["visionScore"]

    messages = []

    kda = (kills + assists) / max(1, deaths)

    if kda >= 4:
        messages.append("Excellente performance globale.")
    elif kda >= 2:
        messages.append("Bonne contribution aux combats.")
    else:
        messages.append("Impact limité dans la partie.")

    if kills >= 10:
        messages.append("Très forte pression offensive.")

    if deaths >= 8:
        messages.append("Beaucoup de morts, attention au positionnement.")

    if gold >= 15000:
        messages.append("Excellent farm.")
    elif gold < 9000:
        messages.append("Farm faible pour la durée du match.")

    if vision < 10:
        messages.append("Vision très faible.")

    return " ".join(messages)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player or "#" not in player:
        return "Format : Summoner#TAG"

    name, tag = player.split("#")

    account = riot(
        f"{MATCH_URL}/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    )

    if not account:
        return "Player not found"

    puuid = account["puuid"]

    summ = riot(
        f"{SUMMONER_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )

    if not summ:
        return "Erreur récupération summoner"

    summoner_id = summ.get("id")

    rank = None

    if summoner_id:
        ranked = riot(
            f"{LEAGUE_URL}/lol/league/v4/entries/by-summoner/{summoner_id}"
        )

        if ranked and len(ranked) > 0:
            rank = ranked[0]

    match_ids = riot(
        f"{MATCH_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
    )

    games = []

    for match_id in match_ids:

        match = riot(
            f"{MATCH_URL}/lol/match/v5/matches/{match_id}"
        )

        if not match:
            continue

        info = match["info"]
        participants = info["participants"]

        player_data = None

        for p in participants:
            if p["puuid"] == puuid:
                player_data = p

        team1 = []
        team2 = []

        for i, p in enumerate(participants):

            pdata = {
                "name": p["summonerName"],
                "champion": p["championName"],
                "gold": p["goldEarned"],
                "items_list": [
                    p["item0"],
                    p["item1"],
                    p["item2"],
                    p["item3"],
                    p["item4"],
                    p["item5"],
                    p["item6"]
                ]
            }

            if i < 5:
                team1.append(pdata)
            else:
                team2.append(pdata)

        game = {
            "win": player_data["win"],
            "champion": player_data["championName"],
            "kills": player_data["kills"],
            "deaths": player_data["deaths"],
            "assists": player_data["assists"],
            "duration": int(info["gameDuration"] / 60),
            "analysis": analyse(player_data),
            "team1": team1,
            "team2": team2
        }

        games.append(game)

    return render_template(
        "results.html",
        games=games,
        summoner=summ,
        rank=rank
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
