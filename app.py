def ai_analysis(games):

    kills = 0
    deaths = 0
    assists = 0
    gold = 0
    wins = 0

    for g in games:

        for p in g["players"]:
            if p["me"]:
                kills += p["kills"]
                deaths += p["deaths"]
                assists += p["assists"]
                gold += p["gold"]

        if g["win"]:
            wins += 1

    total = len(games)

    if total == 0:
        return "Pas assez de données."

    kda = (kills + assists) / max(1, deaths)
    avg_gold = gold / total
    winrate = wins / total * 100

    text = []

    if kda > 3:
        text.append("✔ Bon KDA global.")
    else:
        text.append("⚠ KDA faible, essayez de mourir moins.")

    if avg_gold > 12000:
        text.append("✔ Bon revenu en gold.")
    else:
        text.append("⚠ Gold moyen assez bas.")

    if winrate > 55:
        text.append("✔ Bon winrate.")
    else:
        text.append("⚠ Winrate faible, attention aux décisions midgame.")

    return "<br>".join(text)
