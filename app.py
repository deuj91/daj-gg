from flask import Flask, render_template, request
import requests
import os
import urllib.parse
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
        return "Format: Name#TAG"

    name, tag = player.split("#", 1)

    name_encoded = urllib.parse.quote(name)
    tag_encoded = urllib.parse.quote(tag)

    headers = {
        "X-Riot-Token": RIOT_API_KEY
    }

    try:

        # ACCOUNT
        acc = requests.get(
            f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name_encoded}/{tag_encoded}",
            headers=headers
        ).json()

        puuid = acc["puuid"]

        # SUMMONER
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
        rank_icon = ""

        if league:
            tier = league[0]["tier"]
            div = league[0]["rank"]
            rank = f"{tier} {div}"

            rank_icon = f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{tier.lower()}.png"

        # MATCH LIST
        match_ids = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5",
            headers=headers
        ).json()

        matches = []
        champs = []

        for match_id in match_ids:

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

                items = [
                    p["item0"], p["item1"], p["item2"],
                    p["item3"], p["item4"], p["item5"]
                ]

                pdata = {
                    "name": p["riotIdGameName"],
                    "champ": p["championName"],
                    "kills": p["kills"],
                    "deaths": p["deaths"],
                    "assists": p["assists"],
                    "gold": p["goldEarned"],
                    "items": items
                }

                score = p["kills"] + p["assists"] - p["deaths"]

                if score > best_score:
                    best_score = score
                    mvp = p["riotIdGameName"]

                if p["puuid"] == puuid:
                    champs.append(p["championName"])

                if p["teamId"] == 100:
                    blue.append(pdata)
                else:
                    red.append(pdata)

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
            rank_icon=rank_icon,
            matches=matches,
            top_champs=top_champs
        )

    except Exception as e:
        return f"Error API: {e}"


if __name__ == "__main__":
    app.run()
