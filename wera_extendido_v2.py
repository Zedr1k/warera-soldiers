import itertools

STATS_BASE = {
    "damage": 100,
    "accuracy": 50,
    "crit_chance": 10,
    "crit_damage": 50,
    "armor": 0,
    "hp": 50,
    "hambre": 4,
    "dodge": 0
}

def build_stats_with_equipment(stats_eq):
    return {
        "damage": (STATS_BASE["damage"] + stats_eq["arma_daño"], 20),
        "accuracy": (STATS_BASE["accuracy"] + stats_eq["guantes_acc"], 5),
        "crit_chance": (STATS_BASE["crit_chance"] + stats_eq["arma_critico"], 5),
        "crit_damage": (STATS_BASE["crit_damage"] + stats_eq["casco_crit_damage"], 10),
        "armor": (STATS_BASE["armor"] + stats_eq["chaleco_armor"] + stats_eq["pant_armor"], 4),
        "hp": (50, 10),
        "hambre": (4, 1),
        "dodge": (STATS_BASE["dodge"] + stats_eq["botas_dodge"], 4)
    }

def alloc_cost(k):
    return k * (k + 1) // 2

def total_cost(levels):
    return sum(alloc_cost(lvl) for lvl in levels)

def compute_stats(levels, STATS):
    return {key: base + inc * levels[i] for i, (key, (base, inc)) in enumerate(STATS.items())}

def evaluate_build(stats, food_health=20, battle_duration=7):
    accuracy = min(stats["accuracy"], 100) / 100
    crit_rate = min(stats["crit_chance"], 100) / 100
    crit_multiplier = 1 + (stats["crit_damage"] / 100)

    expected_damage = stats["damage"] * accuracy * ((1 - crit_rate) + crit_rate * crit_multiplier)

    dodge_chance = min(stats.get("dodge", 0), 100) / 100
    damage_taken = max(0.0001, 10 * (1 - stats["armor"] / 100))
    damage_taken *= (1 - dodge_chance)

    max_hp = stats["hp"]
    max_hambre = stats["hambre"]
    total_hambre = max_hambre
    total_hp = max_hp

    for _ in range(battle_duration):
        total_hp += max_hp * 0.1
        total_hambre += max_hambre * 0.1

    total_hp += total_hambre * food_health
    comida_usada = total_hambre
    ataques_totales = total_hp / damage_taken

    return expected_damage * ataques_totales, comida_usada, ataques_totales

def find_best_distribution(levels, STATS, food_health=20, battle_duration=7):
    max_points = 4 * levels
    STAT_KEYS = list(STATS.keys())
    best_score = 0
    best_allocation = None

    def backtrack(i, remaining_points, current):
        nonlocal best_score, best_allocation
        if i == len(STAT_KEYS):
            if remaining_points == 0:
                stats = compute_stats(current, STATS)
                score, _, _ = evaluate_build(stats, food_health, battle_duration)
                if score > best_score:
                    best_score = score
                    best_allocation = (tuple(current), stats, score)
            return

        for lvl in range(0, levels + 1):
            cost = alloc_cost(lvl)
            if cost <= remaining_points:
                current.append(lvl)
                backtrack(i + 1, remaining_points - cost, current)
                current.pop()

    backtrack(0, max_points, [])
    return best_allocation

def evaluate_custom_distribution(levels, STATS, food_health=20, battle_duration=7, level=100):
    if len(levels) != len(STATS):
        raise ValueError(f"Se esperaban {len(STATS)} valores de nivel. Recibido: {len(levels)}")
    if total_cost(levels) > 4 * level:
        raise ValueError("La distribución excede el total de puntos disponibles.")

    stats = compute_stats(levels, STATS)
    score, comida_usada, ataques_totales = evaluate_build(stats, food_health, battle_duration)
    return stats, score, comida_usada, ataques_totales
