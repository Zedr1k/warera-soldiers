# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 17:26:06 2025

@author: d908896
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime, timedelta, timezone

from wera_extendido_v2 import evaluate_custom_distribution, build_stats_with_equipment

API_BASE    = "https://api2.warera.io/trpc"
COUNTRY_ID  = "6813b6d546e731854c7ac835"
PAGE_SIZE   = 100
OUTPUT_CSV  = "country_skill_levels_with_damage.csv"

# Default equipment stats for evaluation
def default_equipment():
    return {
        "arma_daño": 90,
        "arma_critico": 15,
        "guantes_acc": 15,
        "casco_crit_damage": 15,
        "chaleco_armor": 15,
        "pant_armor": 15,
        "botas_dodge": 15
    }
CATEGORIES = {
    "Empresario":  ["companies", "entrepreneurship"],
    "Trabajador":  ["energy", "production"],
    "Soldado":     ["health", "hunger", "attack",
                    "criticalChance", "criticalDamages",
                    "armor", "construction", "precision", "dodge"],
}

# Combat skill order matching build_stats_with_equipment expectations
COMBAT_SKILLS = [
    "attack", "precision", "criticalChance",
    "criticalDamages", "armor", "health", "hunger", "dodge"
]


def call_trpc(endpoint, payload):
    resp = requests.get(
        f"{API_BASE}/{endpoint}",
        params={"batch":"1", "input": json.dumps({"0": payload})}
    )
    resp.raise_for_status()
    return resp.json()[0]["result"]["data"]

def fetch_all_user_ids(country_id):
    """Return list of user IDs in given country."""
    user_ids = []
    cursor = None
    while True:
        payload = {"countryId": country_id, "limit": PAGE_SIZE}
        if cursor:
            payload["cursor"] = cursor
        data = call_trpc("user.getUsersByCountry", payload)
        items = data.get("items", [])
        user_ids.extend(u["_id"] for u in items)
        cursor = data.get("nextCursor")
        if not cursor:
            break
        time.sleep(0.2)
    return user_ids

def fetch_user_record(user_id):
    d = call_trpc("user.getUserLite", {"userId": user_id})
    rec = {
        "username": d.get("username", user_id),
        "level":    d.get("leveling", {}).get("level", 0)
    }
    # inactive si último login >3 días
    last = d.get("dates", {}).get("lastConnectionAt")
    if last:
        dt = datetime.fromisoformat(last.replace("Z","+00:00"))
        rec["active"] = (datetime.now(timezone.utc) - dt) <= timedelta(days=1.5)
    else:
        rec["active"] = False

    skills = d.get("skills", {})
    for skill, info in skills.items():
        rec[skill] = info.get("level", 1)

    # Buff or Debuff condition
    buffs = d.get("buffs", {})
    now = datetime.now(timezone.utc)

    if "buffCodes" in buffs:
        rec["Current Condition"] = "Buffed"
        end_time = buffs.get("buffEndAt")
    elif "debuffCodes" in buffs:
        rec["Current Condition"] = "Debuff"
        end_time = buffs.get("debuffEndAt")
    else:
        rec["Current Condition"] = "None"
        end_time = None

    if end_time:
        dt_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        delta = dt_end - now
        if delta.total_seconds() > 0:
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes = remainder // 60
            rec["Tiempo restante"] = f"{hours}h {minutes}m"
        else:
            rec["Tiempo restante"] = "Expired"
    else:
        rec["Tiempo restante"] = "-"
        
    # wealth y damage
    ranks = d.get("rankings", {})
    rec["wealthValue"] = round(ranks.get("userWealth", {}).get("value", 0))
    rec["damageValue"] = ranks.get("userDamages", {}).get("value", 0)
    rec["damageWeek"]  = ranks.get("userWeeklyDamages", {}).get("value", 0)

    return rec

def points_spent(level):
    # cost sumar desde nivel1 hasta nivel L: sum(k=1..L) k = (L+1)*L/2
    return (level) * (level + 1) // 2

def assign_roles(rec):
    # calcular puntos gastados en cada skill
    spent = {}
    total_spent = 0
    for k,v in rec.items():
        if k in CATEGORIES["Soldado"] + CATEGORIES["Empresario"] + CATEGORIES["Trabajador"]:
            p = points_spent(v)
            spent[k] = p
            total_spent += p
    if total_spent == 0:
        total_spent = 1

    # porcentaje por categoría
    cat_perc = {}
    for cat, skills in CATEGORIES.items():
        s = sum(spent.get(skill, 0) for skill in skills)
        cat_perc[cat] = s / total_spent

    # primary >80%
    primary = "Polivalente"
    for cat, p in cat_perc.items():
        if p >= 0.85:
            primary = f"Super {cat}"
            break
        elif p >= 0.70:
            primary = cat
            break
    # secondary >40% y distinta de primary
    secondary = [cat for cat,p in cat_perc.items() if cat not in primary and p >= 0.4]

    rec["primaryRole"]    = primary
    rec["secondaryRoles"] = ", ".join(secondary) if secondary else ""
    return rec

def calculate_damage(rec, food_health=30, battle_duration=7):
    """
    Dado un registro de usuario con niveles de COMBAT_SKILLS,
    calcula daño esperado y estadísticas usando evaluate_custom_distribution
    con el equipamiento por defecto.
    """
    # Extraer niveles de combate en el orden correcto
    levels = [rec.get(skill, 0) for skill in COMBAT_SKILLS]
    # Obtener estadísticas de equipo por defecto (sin niveles)
    equip_stats = build_stats_with_equipment(default_equipment())
    # Evaluar build personalizada para niveles de usuario
    # Usamos level cap igual al nivel del jugador para validar
    max_level = rec.get("level", max(levels))
    stats, score, food_used, total_attacks = evaluate_custom_distribution(
        levels, equip_stats, food_health, battle_duration, max_level
    )
    # Guardar resultados en el registro
    rec["stats"] = stats
    rec["calculated_damage"] = round(score)
    return rec


def main():
    print("Recopilando usuarios del país...")
    user_ids = fetch_all_user_ids(COUNTRY_ID)
    print(f"Usuarios encontrados: {len(user_ids)}\n")

    records = []
    for i, uid in enumerate(user_ids, start=1):
        rec = fetch_user_record(uid)
        rec = assign_roles(rec)
        rec = calculate_damage(rec)
        status = "INACTIVO" if rec.get("inactive") else "ACTIVO"
        print(
            f"[{i}/{len(user_ids)}] {rec['username']} | lvl={rec.get('level')} | dmg={rec['calculated_damage']:.1f}"
            f" | food={rec['food_used']:.1f} | attacks={rec['total_attacks']:.1f} | status={status}"
        )
        records.append(rec)
        time.sleep(0.1)

    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n📊 Exportado CSV a `{OUTPUT_CSV}` con daño calculado y stats.")

if __name__ == "__main__":
    main()
