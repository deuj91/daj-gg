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

    try:

        player = request.args.get("player")

        if not player or "#" not in player:
            return "Format: Name#TAG"

        name, tag = player.split("#", 1)

        name = urllib.parse.quote(name)
        tag = urllib.parse.quote(tag)

        headers = {
            "X-Riot-Token": RIOT_API_KEY
        }

        # ACCOUNT API
        acc_res = requests.get(
            f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
            headers=headers
        )

        if acc_res.status_code != 200:
            return f"Account API error {acc_res.status_code}"

        acc = acc_res.json()
        puuid = acc.get("puuid")

        if not puuid:
            return "PUUID not found"

        # SUMMONER API
        summoner_res = requests.get(
            f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}",
            headers=headers
        )

        if summoner_res.status_code != 200:
            return f"Summoner API error {summoner_res.status_code}"

        summoner = summoner_res.json()

        level = summoner.get("summonerLevel", 0)
        icon = summoner.get("profileIconId", 29)

        # RANK API (via puuid)
        league_res = requests.get(
            f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}",
            headers=headers
        )

        if league_res.status_code == 200:
            league = league_res.json()
        else:
            league = []

        rank = "Unranked"

        if league:
            tier = league[0].get("tier", "")
            division = league[0].get("rank", "")
            rank = f"{tier} {division}"

        # MATCH LIST
        matches_res = requests.get(
            f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5",
            headers=headers
        )

        if matches_res.status_code != 200:
            return "Match history error"

        match_ids = matches_res.json()

        matches = []
        champs = []

        for match_id in match_ids:

            match_res = requests.get(
                f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}",
                headers=headers
            )

            if match_res.status_code != 200:
                continue

            data = match_res.json()
            info = data.get("info", {})

            blue = []
            red = []

            mvp = ""
            best_score = -999

            for p in info.get("participants", []):

                items = [
                    p.get("item0", 0),
                    p.get("item1", 0),
                    p.get("item2", 0),
                    p.get("item3", 0),
                    p.get("item4", 0),
                    p.get("item5", 0)
                ]

                player_data = {
                    "name": p.get("riotIdGameName", ""),
                    "champion": p.get("championName", ""),
                    "kills": p.get("kills", 0),
                    "deaths": p.get("deaths", 0),
                    "assists": p.get("assists", 0),
                    "gold": p.get("goldEarned", 0),
                    "items": items
                }

                score = player_data["kills"] + player_data["assists"] - player_data["deaths"]

                if score > best_score:
                    best_score = score
                    mvp = player_data["name"]

                if p.get("puuid") == puuid:
                    champs.append(p.get("championName", ""))

                if p.get("teamId") == 100:
                    blue.append(player_data)
                else:
                    red.append(player_data)

            matches.append({
                "blue": blue,
                "red": red,
                "mode": info.get("gameMode", ""),
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

    except Exception as e:
        return f"Server error: {e}"


if __name__ == "__main__":
    app.run()
