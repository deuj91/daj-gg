import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

SUMMONER_URL = "https://euw1.api.riotgames.com"
MATCH_URL = "https://europe.api.riotgames.com"
LEAGUE_URL = "https://euw1.api.riotgames.com"

def riot(url):
    headers = {"X-Riot-Token": API_KEY}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None
    return r.json()


def analyse_game(p):

    score = p["kills"] + p["assists"] - p["deaths"]

    analysis = []

    if p["kills"] >= 10:
        analysis.append("Très forte pression offensive.")

    if p["deaths"] >= 7:
        analysis.append("Beaucoup de morts, attention au positionnement.")

    if p["visionScore"] < 15:
        analysis.append("Vision trop faible. Pense à ward davantage.")

    if p["goldEarned"] > 13000:
        analysis.append("Très bon farm et génération de gold.")

    if p["damageDealtToChampions"] > 20000:
        analysis.append("Gros impact en teamfight.")

    if score > 10:
        analysis.append("Game très solide avec bon impact global.")

    if len(analysis) == 0:
        analysis.append("Game assez neutre avec impact limité.")

    return " ".join(analysis)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    name, tag = player.split("#")

    account = riot(
        f"{MATCH_URL}/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    )

    puuid = account["puuid"]

    summ = riot(
        f"{SUMMONER_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )

    ranked = riot(
        f"{LEAGUE_URL}/lol/league/v4/entries/by-summoner/{summ['id']}"
    )

    rank = None
    if ranked and len(ranked) > 0:
        rank = ranked[0]

    match_ids = riot(
        f"{MATCH_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=15"
    )

    games = []

    for match_id in match_ids:

        match = riot(
            f"{MATCH_URL}/lol/match/v5/matches/{match_id}"
        )

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
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
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
            "duration": int(info["gameDuration"] / 60),
            "win": player_data["win"],
            "champion": player_data["championName"],
            "kills": player_data["kills"],
            "deaths": player_data["deaths"],
            "assists": player_data["assists"],
            "analysis": analyse_game(player_data),
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
