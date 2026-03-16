from flask import Flask, render_template, request
import requests
import os
from collections import Counter

app = Flask(__name__)

RIOT_API_KEY = os.getenv("RIOT_API_KEY")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player or "#" not in player:
        return "Use format: name#tag"

    name, tag = player.split("#")

    headers = {"X-Riot-Token": RIOT_API_KEY}

    # ACCOUNT API
    acc = requests.get(
        f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
        headers=headers
    ).json()

    puuid = acc.get("puuid")

    if not puuid:
        return "Player not found"

    # SUMMONER DATA
    summoner = requests.get(
        f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}",
        headers=headers
    ).json()

    level = summoner.get("summonerLevel", 0)
    icon = summoner.get("profileIconId", 29)

    # RANK
    league = requests.get(
        f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}",
        headers=headers
    ).json()

    rank = "Unranked"

    if league:
        tier = league[0]["tier"]
        division = league[0]["rank"]
        rank = f"{tier} {division}"

    # MATCH LIST
    matches_ids = requests.get(
        f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5",
        headers=headers
    ).json()

    matches = []
    champs = []

    for match_id in matches_ids:

        data = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
            headers=headers
        ).json()

        info = data["info"]

        blue = []
        red = []

        best_score = -999
        mvp = ""

        for p in info["participants"]:

            score = p["kills"] + p["assists"] - p["deaths"]

            if score > best_score:
                best_score = score
                mvp = p["riotIdGameName"]

            player_data = {
                "name": p["riotIdGameName"],
                "champ": p["championName"],
                "k": p["kills"],
                "d": p["deaths"],
                "a": p["assists"],
                "gold": p["goldEarned"],
                "items": [
                    p["item0"],
                    p["item1"],
                    p["item2"],
                    p["item3"],
                    p["item4"],
                    p["item5"]
                ]
            }

            if p["teamId"] == 100:
                blue.append(player_data)
            else:
                red.append(player_data)

            if p["puuid"] == puuid:
                champs.append(p["championName"])

        matches.append({
            "blue": blue,
            "red": red,
            "mode": info["gameMode"],
            "mvp": mvp
        })

    top_champs = Counter(champs).most_common(5)

    return render_template(
        "profile.html",
        name=name,
        tag=tag,
        level=level,
        icon=icon,
        rank=rank,
        matches=matches,
        top_champs=top_champs
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
