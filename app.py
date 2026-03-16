import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

REGION = "europe"
PLATFORM = "euw1"


def riot(url):
    headers = {"X-Riot-Token": API_KEY}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None
    return r.json()


def performance_score(k, d, a, gold):

    score = k*3 + a*2 - d + gold/1000

    if score > 30:
        return "S+"
    elif score > 25:
        return "S"
    elif score > 20:
        return "A"
    elif score > 15:
        return "B"
    else:
        return "C"


def ai_analysis(stats):

    report = []

    if stats["kda"] > 3:
        report.append("✔ Good KDA overall.")
    else:
        report.append("⚠ Low KDA, try to die less.")

    if stats["winrate"] > 55:
        report.append("✔ Good winrate.")
    else:
        report.append("⚠ Winrate could improve.")

    if stats["gold"] > 12000:
        report.append("✔ Good gold income.")
    else:
        report.append("⚠ Gold income is low.")

    return report


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if "#" not in player:
        return "Use format name#tag"

    name, tag = player.split("#")

    account = riot(
        f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    )

    puuid = account["puuid"]

    summoner = riot(
        f"https://{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )

    ranked = riot(
        f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    )

    rank = ranked[0] if ranked else None

    matches = riot(
        f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=20"
    )

    games = []

    kills = deaths = assists = gold_total = wins = 0
    champions = {}

    for match_id in matches:

        match = riot(
            f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        )

        info = match["info"]

        blue = []
        red = []

        mvp_score = 0
        mvp_name = ""

        for p in info["participants"]:

            score = p["kills"]*3 + p["assists"]*2 - p["deaths"] + p["goldEarned"]/1000

            if score > mvp_score:
                mvp_score = score
                mvp_name = p["summonerName"]

            data = {
                "name": p["summonerName"],
                "champ": p["championName"],
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
                "gold": p["goldEarned"],
                "items": [
                    p["item0"], p["item1"], p["item2"],
                    p["item3"], p["item4"], p["item5"]
                ],
                "score": performance_score(
                    p["kills"], p["deaths"], p["assists"], p["goldEarned"]
                )
            }

            if p["puuid"] == puuid:

                kills += p["kills"]
                deaths += p["deaths"]
                assists += p["assists"]
                gold_total += p["goldEarned"]

                if p["win"]:
                    wins += 1

                champions[p["championName"]] = champions.get(
                    p["championName"], 0) + 1

            if p["teamId"] == 100:
                blue.append(data)
            else:
                red.append(data)

        games.append({
            "mode": info["gameMode"],
            "duration": int(info["gameDuration"] / 60),
            "blue": blue,
            "red": red,
            "win": p["win"],
            "mvp": mvp_name
        })

    total = len(games)

    stats = {
        "kda": (kills + assists) / max(1, deaths),
        "winrate": wins / max(1, total) * 100,
        "gold": gold_total / max(1, total)
    }

    analysis = ai_analysis(stats)

    top_champs = sorted(
        champions.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    return render_template(
        "results.html",
        games=games,
        summoner=summoner,
        rank=rank,
        stats=stats,
        analysis=analysis,
        champs=top_champs
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
