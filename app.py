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

    tips = []

    if p["kills"] >= 8:
        tips.append("Très bon impact offensif.")

    if p["deaths"] >= 7:
        tips.append("Trop de morts, attention au positionnement.")

    if p["visionScore"] < 15:
        tips.append("Vision faible. Utilise plus de wards.")

    if p["goldEarned"] > 13000:
        tips.append("Très bon farm et génération de gold.")

    if not tips:
        tips.append("Game correcte mais améliorable.")

    return " ".join(tips)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player or "#" not in player:
        return "Format: Pseudo#TAG"

    name, tag = player.split("#")

    account = riot(
        f"{MATCH_URL}/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    )

    if not account:
        return "Player introuvable"

    puuid = account["puuid"]

    summ = riot(
        f"{SUMMONER_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )

    if not summ:
        return "Erreur récupération summoner"

    ranked = riot(
        f"{LEAGUE_URL}/lol/league/v4/entries/by-summoner/{summ['id']}"
    )

    rank = None
    if ranked and len(ranked) > 0:
        rank = ranked[0]

    match_ids = riot(
        f"{MATCH_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10"
    )

    games = []

    if not match_ids:
        return render_template(
            "results.html",
            games=[],
            summoner=summ,
            rank=rank
        )

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

        if not player_data:
            continue

        team1 = []
        team2 = []

        for i, p in enumerate(participants):

            pdata = {
                "name": p["summonerName"],
                "champion": p["championName"],
                "gold": p["goldEarned"],
                "items": [
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
