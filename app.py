from flask import Flask, render_template, request, redirect
import requests
import time

app = Flask(__name__)

API_KEY = "RGAPI-xxxxxxxxxxxxxxxx"
REGION = "europe"
MATCH_REGION = "europe"

CACHE = {}


def cached_request(url):

    if url in CACHE and time.time() - CACHE[url]["time"] < 60:
        return CACHE[url]["data"]

    r = requests.get(url)

    if r.status_code != 200:
        return None

    data = r.json()

    CACHE[url] = {
        "data": data,
        "time": time.time()
    }

    return data


def get_rank_icon(tier):
    tier = tier.lower()
    return f"https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-{tier}.png"


def player_score(player):

    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]

    cs = player["totalMinionsKilled"] + player["neutralMinionsKilled"]

    vision = player["visionScore"]

    damage = player["totalDamageDealtToChampions"]

    kda = (kills + assists) / max(1, deaths)

    score = 0

    score += min(kda * 10, 40)
    score += min(cs / 10, 20)
    score += min(vision, 20)
    score += min(damage / 2000, 20)

    return int(score)


def win_probability(player):

    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]

    cs = player["totalMinionsKilled"]

    gold = player["goldEarned"]

    damage = player["totalDamageDealtToChampions"]

    score = 0

    score += (kills + assists) * 2
    score -= deaths * 2
    score += cs / 10
    score += gold / 1000
    score += damage / 5000

    return max(0, min(int(score), 100))


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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():

    player = request.args.get("player")

    if not player or "#" not in player:
        return redirect("/")

    name, tag = player.split("#")

    account_url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={API_KEY}"

    account = cached_request(account_url)

    if not account:
        return render_template("index.html")

    puuid = account["puuid"]

    summoner_url = f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={API_KEY}"

    summoner = cached_request(summoner_url)

    summoner_id = summoner["id"]

    rank_url = f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={API_KEY}"

    ranked_data = cached_request(rank_url)

    rank = "Unranked"
    rank_icon = ""

    if ranked_data and len(ranked_data) > 0:

        ranked = ranked_data[0]

        tier = ranked["tier"]
        div = ranked["rank"]

        rank = f"{tier} {div}"

        rank_icon = get_rank_icon(tier)

    matches_url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5&api_key={API_KEY}"

    match_ids = cached_request(matches_url)

    games = []

    for match_id in match_ids:

        url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"

        match = cached_request(url)

        if not match:
            continue

        info = match["info"]

        participants = info["participants"]

        player_data = None

        for p in participants:
            if p["puuid"] == puuid:
                player_data = p
                break

        if not player_data:
            continue

        champion = player_data["championName"]

        kills = player_data["kills"]
        deaths = player_data["deaths"]
        assists = player_data["assists"]

        cs = player_data["totalMinionsKilled"]

        gold = player_data["goldEarned"]

        vision = player_data["visionScore"]

        result = "Victory" if player_data["win"] else "Defeat"

        champion_img = f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/{champion}.png"

        items = []

        for i in range(7):

            item = player_data[f"item{i}"]

            if item != 0:
                items.append(
                    f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/item/{item}.png"
                )

        team = []
        allies = []

        team_id = player_data["teamId"]

        for p in participants:

            if p["teamId"] == team_id:
                team.append(p)

            if p["teamId"] == team_id and p["puuid"] != puuid:

                ally_items = []

                for i in range(7):

                    item = p[f"item{i}"]

                    if item != 0:
                        ally_items.append(
                            f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/item/{item}.png"
                        )

                allies.append({
                    "name": p.get("riotIdGameName", "Unknown"),
                    "champion": p["championName"],
                    "champion_img": f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/{p['championName']}.png",
                    "kda": f"{p['kills']}/{p['deaths']}/{p['assists']}",
                    "items_list": ally_items
                })

        score = player_score(player_data)

        probability = win_probability(player_data)

        feeder = detect_feeder(team)

        games.append({

            "champion_img": champion_img,
            "kda": f"{kills}/{deaths}/{assists}",
            "cs": cs,
            "gold": gold,
            "vision": vision,
            "result": result,
            "items_list": items,
            "score": score,
            "probability": probability,
            "feeder": feeder,
            "allies": allies

        })

    return render_template(
        "index.html",
        games=games,
        player=player,
        rank=rank,
        rank_icon=rank_icon
    )


if __name__ == "__main__":
    app.run(debug=True)
