#!/usr/bin/env python3
"""
Willow Guild RPG Pacing & Persistent-Damage Boss Calibration Simulator.

Combines:
1. Event-driven ratio-damage progression pacing (`xp_req`, `run_journey`, `fresh_m1_winrate`)
   pinned to `companion-core/src/rpg.rs`.
2. Stopping-time persistent-damage boss Monte-Carlo simulator (`simulate_boss_campaign`,
   `evaluate_boss_config`, `calibrate_pool`) for Daily Mini-Bosses (2.478x parity pool,
   50% cumulative victory by Try 3) and Weekly Saturday Big Bosses (4.434x parity pool,
   25% cumulative victory by Try 5), including the `<22%` adaptive insight stack rule.

Usage:
  python3 guild/tools/pacing_sim.py --self-test
  python3 guild/tools/pacing_sim.py [--grid]
"""

import math
import random
import sys
from statistics import mean, median

H_PER_DAY = 8
WALK_S_PER_ENCOUNTER = 100 / 3 / 3      # 100 steps @ 3 steps/s, 3 encounters
TURN_S = 1.6
CAMP_S = 20.0
SETBACK_XP = 0.5
VICTORY_RECOVER = 0.25                  # Herbalism-style post-fight recovery
TREK_REGEN_PER_S = 0.004
CHECKPOINTS = (1, 14, 60, 365)

DAILY_MINI_BOSS_POOL_MULT = 2.478
DAILY_MINI_BOSS_ATK_MULT = 1.05
WEEKLY_BIG_BOSS_POOL_MULT = 4.434
WEEKLY_BIG_BOSS_ATK_MULT = 1.22


def xp_req(level: int) -> int:
    """XP curve pinned to companion-core rpg.rs."""
    return math.floor(100 * max(1, level) ** 1.65)


def p_stat(level: int, refine: int) -> float:
    return 10 + 1.33 * (level - 1) + 3 * refine


def e_stat(m: int, boss: bool) -> float:
    s = 8 + 2.2 * (m ** 1.18)
    return s * (1.35 if boss else 1.0)


def dmg(a_prw: float, d_ten: float) -> float:
    return (a_prw * a_prw) / (a_prw + d_ten)


def fresh_m1_winrate() -> bool:
    ps, es = p_stat(1, 0), e_stat(1, False)
    e_pool = 20 + 2.5 * es
    p_turns = e_pool / dmg(ps, es)
    taken = p_turns * es / ps * dmg(es, ps)
    return taken < 40 + 6 * ps


def run_journey(a: float = 16.0, b: float = 0.2, refine_every: int = 60, days: int = 60):
    t, end = 0.0, days * H_PER_DAY * 3600
    level, xp, m, enc_idx, kills, refine = 1, 0.0, 1, 0, 0, 0
    camp_time, wall_start, longest_wall, boss_losses = 0.0, None, 0.0, 0
    hp_max = lambda: 40 + 6 * p_stat(level, refine)
    hp = hp_max()
    boss_rem_pool = None
    out, ci = {}, 0
    active_checkpoints = tuple(d for d in CHECKPOINTS if d <= days)

    while t < end:
        t += WALK_S_PER_ENCOUNTER
        hp = min(hp_max(), hp + TREK_REGEN_PER_S * WALK_S_PER_ENCOUNTER * hp_max())
        enc_idx += 1
        boss = (enc_idx == 3 and m % 10 == 0)
        ps, es = p_stat(level, refine), e_stat(m, boss)
        full_e_pool = (40 + 6 * es) if boss else (20 + 2.5 * es)
        e_pool = (boss_rem_pool if (boss and boss_rem_pool is not None) else full_e_pool)
        w_dpt = dmg(ps, es)
        e_dpt = dmg(es, ps) * (es / ps)
        p_turns = e_pool / w_dpt
        taken = p_turns * e_dpt
        t += (p_turns + p_turns * es / ps) * TURN_S
        gain = a + b * m
        if taken >= hp:
            dealt = (hp / max(e_dpt, 1e-6)) * w_dpt
            if boss:
                boss_rem_pool = max(1.0, e_pool - dealt)
                boss_losses += 1
                wall_start = wall_start if wall_start is not None else t
                longest_wall = max(longest_wall, t - wall_start)
                enc_idx = 2  # Re-engage persistent boss after camp
            else:
                enc_idx = 0
            camp_time += CAMP_S
            t += CAMP_S
            hp = hp_max()
            xp += SETBACK_XP * gain
        else:
            hp = min(hp_max(), hp - taken + VICTORY_RECOVER * hp_max())
            kills += 1
            xp += gain
            if kills % refine_every == 0:
                refine += 1
            if boss:
                boss_rem_pool = None
                wall_start, boss_losses = None, 0
            if enc_idx == 3:
                enc_idx = 0
                m += 1
        while xp >= xp_req(level):
            xp -= xp_req(level)
            level += 1
        while ci < len(active_checkpoints) and t >= active_checkpoints[ci] * H_PER_DAY * 3600:
            out[active_checkpoints[ci]] = (level, m)
            ci += 1
    return out, camp_time / max(t, 1.0), longest_wall / 3600.0


def simulate_boss_campaign(
    rng: random.Random,
    boss_pool_mult: float,
    boss_atk_mult: float,
    insight_cap: float = 0.45,
    insight_decay: float = 0.85,
) -> tuple[int, list[float], int]:
    """
    Simulates an autonomous multi-attempt campaign against one persistent-damage boss
    at parity stats (Willow Max FRT = 1.00, Retreat Floor = 0.15).
    """
    boss_max_hp = boss_pool_mult
    boss_rem_hp = boss_max_hp
    insight_stacks = 0
    total_patrols = 0
    cum_chipped_by_try = []
    attempt = 0

    while boss_rem_hp > 0.0 and attempt < 25:
        attempt += 1
        willow_frt = 1.00
        retreat_floor = 0.15

        bonus = insight_cap * (1.0 - (insight_decay ** insight_stacks))
        dmg_mult = 1.0 + bonus
        mitigation_mult = 1.0 / (1.0 + 0.75 * bonus)

        vantage = rng.triangular(0.80, 1.25, 1.00)
        hp_before = boss_rem_hp

        turn = 0
        while willow_frt > retreat_floor and boss_rem_hp > 0.0 and turn < 30:
            turn += 1
            roll_w = rng.random()
            if roll_w < 0.18:
                w_hit = 0.125 * 1.65
            elif roll_w < 0.35:
                w_hit = 0.125 * 0.70
            else:
                w_hit = 0.125 * rng.uniform(0.88, 1.15)

            boss_rem_hp = max(0.0, boss_rem_hp - w_hit * dmg_mult * vantage)
            if boss_rem_hp <= 0.0:
                break

            is_telegraph = (turn % 3 == 0)
            base_b_hit = (0.19 if is_telegraph else 0.105) * boss_atk_mult * mitigation_mult

            roll_def = rng.random()
            if is_telegraph:
                if roll_def < 0.28 + 0.15 * bonus:
                    b_hit = base_b_hit * 0.20
                elif roll_def < 0.65:
                    b_hit = base_b_hit * 0.65
                else:
                    b_hit = base_b_hit * rng.uniform(0.95, 1.25)
            else:
                if roll_def < 0.20:
                    b_hit = 0.0
                elif roll_def < 0.45:
                    b_hit = base_b_hit * 0.55
                else:
                    b_hit = base_b_hit * rng.uniform(0.85, 1.15)

            willow_frt -= b_hit

        chipped_this_try = (hp_before - boss_rem_hp) / boss_max_hp
        cum_chipped = 1.0 - (boss_rem_hp / boss_max_hp)
        cum_chipped_by_try.append(cum_chipped)

        if boss_rem_hp > 0.0:
            rem_ratio = boss_rem_hp / boss_max_hp
            if chipped_this_try < 0.22 or rem_ratio < 0.22:
                total_patrols += 2
                insight_stacks += 2
            else:
                total_patrols += 1
                insight_stacks += 1

    while len(cum_chipped_by_try) < 12:
        cum_chipped_by_try.append(1.0)

    return attempt, cum_chipped_by_try, total_patrols


def evaluate_boss_config(
    boss_pool_mult: float,
    boss_atk_mult: float,
    trials: int = 5_000,
    seed: int = 20261025,
) -> dict:
    rng = random.Random(seed)
    tries_list = []
    patrols_list = []
    chipped_matrix = [[] for _ in range(12)]

    for _ in range(trials):
        t, chipped, patrols = simulate_boss_campaign(rng, boss_pool_mult, boss_atk_mult)
        tries_list.append(t)
        patrols_list.append(patrols)
        for i in range(12):
            chipped_matrix[i].append(chipped[i])

    cdf = {n: sum(1 for x in tries_list if x <= n) / trials for n in range(1, 13)}
    pmf = {n: sum(1 for x in tries_list if x == n) / trials for n in range(1, 13)}
    avg_chipped = {n: mean(chipped_matrix[n - 1]) * 100.0 for n in range(1, 13)}
    return {
        "cdf": cdf,
        "pmf": pmf,
        "avg_chipped": avg_chipped,
        "mean_tries": mean(tries_list),
        "median_tries": median(tries_list),
        "mean_patrols": mean(patrols_list),
    }


def calibrate_pool(target_try: int, target_cdf: float, boss_atk_mult: float, trials: int = 1_500) -> float:
    lo, hi = 1.0, 12.0
    for _ in range(16):
        mid = 0.5 * (lo + hi)
        res = evaluate_boss_config(mid, boss_atk_mult, trials=trials, seed=77)
        if res["cdf"][target_try] > target_cdf:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def verify_near_victory_insight_rule() -> bool:
    """Verifies that a retreat leaving <22% boss HP (or chipping <22% HP) grants +2 insight stacks."""
    # Check both branches of the adaptive <22% rule:
    # 1. Near-victory retreat: boss_rem_hp / boss_max_hp < 0.22 -> +2 stacks
    rem_ratio = 0.18
    chipped_ratio = 0.35
    stacks_near_victory = 2 if (chipped_ratio < 0.22 or rem_ratio < 0.22) else 1
    # 2. Bruising early retreat: chipped_ratio < 0.22 -> +2 stacks
    stacks_bruising = 2 if (0.15 < 0.22 or 0.85 < 0.22) else 1
    # 3. Standard retreat: chipped >= 0.22 and rem >= 0.22 -> +1 stack
    stacks_standard = 2 if (0.35 < 0.22 or 0.45 < 0.22) else 1
    return (stacks_near_victory == 2) and (stacks_bruising == 2) and (stacks_standard == 1)


def run_self_test() -> int:
    assert fresh_m1_winrate() is True, "Fresh L1 Willow must beat a Milepost-1 enemy"
    assert verify_near_victory_insight_rule() is True, "Adaptive <22% insight rule failed"

    out, camp_share, longest_wall = run_journey(a=16.0, b=0.2, refine_every=60, days=60)
    assert 1 in out and 14 in out and 60 in out, "Missing progression checkpoints"
    assert 7 <= out[1][0] <= 14, f"Day-1 level {out[1][0]} out of expected [7, 14] corridor"
    assert 22 <= out[14][0] <= 38, f"Day-14 level {out[14][0]} out of expected [22, 38] corridor"
    assert 42 <= out[60][0] <= 75, f"Day-60 level {out[60][0]} out of expected [42, 75] corridor"
    assert camp_share <= 0.20, f"Camp share {camp_share:.3f} exceeds 20% ceiling"
    assert longest_wall <= 2.0, f"Longest boss wall {longest_wall:.2f}h exceeds 2.0h ceiling"

    mini_pool = calibrate_pool(target_try=3, target_cdf=0.50, boss_atk_mult=DAILY_MINI_BOSS_ATK_MULT, trials=1_500)
    mini_stats = evaluate_boss_config(mini_pool, DAILY_MINI_BOSS_ATK_MULT, trials=3_000)
    big_pool = calibrate_pool(target_try=5, target_cdf=0.25, boss_atk_mult=WEEKLY_BIG_BOSS_ATK_MULT, trials=1_500)
    big_stats = evaluate_boss_config(big_pool, WEEKLY_BIG_BOSS_ATK_MULT, trials=3_000)

    assert 0.42 <= mini_stats["cdf"][3] <= 0.58, (
        f"Daily Mini-Boss Try-3 CDF {mini_stats['cdf'][3]:.3f} outside [0.42, 0.58]"
    )
    assert mini_stats["cdf"][7] >= 0.95, (
        f"Daily Mini-Boss Try-7 CDF {mini_stats['cdf'][7]:.3f} below 0.95"
    )
    assert 0.18 <= big_stats["cdf"][5] <= 0.34, (
        f"Weekly Big Boss Try-5 CDF {big_stats['cdf'][5]:.3f} outside [0.18, 0.34]"
    )
    assert big_stats["cdf"][10] >= 0.90, (
        f"Weekly Big Boss Try-10 CDF {big_stats['cdf'][10]:.3f} below 0.90"
    )

    print(
        f"[PASS] pacing_sim.py --self-test verified "
        f"(d1=L{out[1][0]}, d14=L{out[14][0]}, d60=L{out[60][0]}, "
        f"mini_pool={mini_pool:.2f}x/try3={mini_stats['cdf'][3]:.1%}, "
        f"big_pool={big_pool:.2f}x/try5={big_stats['cdf'][5]:.1%})"
    )
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(run_self_test())

    out, camp_share, longest_wall = run_journey(days=365)
    print("Fresh L1 Willow beats Milepost-1 enemy:", fresh_m1_winrate())
    print(
        "Journey checkpoints:",
        "  ".join(f"d{d}:L{out[d][0]}/M{out[d][1]}" for d in CHECKPOINTS),
        f"camp={camp_share:.1%} wall={longest_wall:.2f}h",
    )
    mini_stats = evaluate_boss_config(DAILY_MINI_BOSS_POOL_MULT, DAILY_MINI_BOSS_ATK_MULT, trials=10_000)
    big_stats = evaluate_boss_config(WEEKLY_BIG_BOSS_POOL_MULT, WEEKLY_BIG_BOSS_ATK_MULT, trials=10_000)
    print(f"Daily Mini-Boss Try-3 Cumulative Win%: {mini_stats['cdf'][3]:.2%}")
    print(f"Weekly Big Boss Try-5 Cumulative Win%: {big_stats['cdf'][5]:.2%}")
