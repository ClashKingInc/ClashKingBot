"""Offline, bounded troop-overlap family prototype for frozen Army Lab exports.

No database, network, scheduler, or production writes. Python standard library only.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

SUPPORT = {
    "Archer", "Barbarian", "Goblin", "Sneaky Goblin", "Minion",
    "Wall Breaker", "Super Wall Breaker", "Headhunter", "Healer",
    "Druid", "Apprentice Warden",
}
MIN_HOUSING = 200
MIN_OVERLAP = 0.80
MAX_FAMILIES = 48


def load_static(path: Path) -> dict[int, dict]:
    document = json.loads(path.read_text())
    groups = document.values() if isinstance(document, dict) else [document]
    return {int(item["_id"]): item for group in groups for item in group if "_id" in item}


def parse_code(code: str) -> tuple[collections.Counter[int], tuple[int, ...]]:
    """Extract main troops and setup IDs from an Army Lab share code."""
    sections = re.findall(r"[hidus][^hidus]*", code)
    if "".join(sections) != code or not sections:
        raise ValueError(f"Invalid share code: {code[:60]}")
    troops: collections.Counter[int] = collections.Counter()
    equipment: set[int] = set()
    spells: collections.Counter[int] = collections.Counter()
    for section in sections:
        marker, value = section[0], section[1:]
        if marker == "h":
            equipment.update(90000000 + int(x) for x in re.findall(r"[e_](\d+)", value))
        elif marker in {"u", "s"}:
            for item in value.split("-"):
                match = re.fullmatch(r"(\d+)x(\d+)", item)
                if not match:
                    raise ValueError(f"Invalid component: {item}")
                quantity, item_id = map(int, match.groups())
                if marker == "u":
                    troops[4000000 + item_id] += quantity
                else:
                    spells[26000000 + item_id] += quantity
    # Exact setup key is deliberately separate from troop-family identity.
    setup = tuple(sorted(equipment | {spell for spell, count in spells.items() if count >= 3}))
    return troops, setup


def troop_housing(code: str, static: dict[int, dict]) -> tuple[dict[int, int], tuple[int, ...]]:
    troops, setup = parse_code(code)
    full = {
        item_id: count * max(1, int(static.get(item_id, {}).get("housing_space") or 1))
        for item_id, count in troops.items()
        if static.get(item_id, {}).get("production_building") != "Workshop"
    }
    total = sum(full.values())
    weighted = {
        item_id: amount for item_id, amount in full.items()
        if static.get(item_id, {}).get("name") not in SUPPORT or amount > total * 0.10
    }
    return weighted, setup


def overlap(a: dict[int, int], b: dict[int, int]) -> float:
    denominator = max(sum(a.values()), sum(b.values()))
    return sum(min(value, b.get(item_id, 0)) for item_id, value in a.items()) / denominator if denominator else 0.0


def signature(troops: dict[int, int], static: dict[int, dict]) -> tuple[int, ...]:
    total = sum(troops.values())
    fighters = {item_id: value for item_id, value in troops.items()
                if static.get(item_id, {}).get("name") not in SUPPORT}
    dominant = sorted(item_id for item_id, value in fighters.items() if value >= total * 0.25)
    if dominant:
        return tuple(dominant)
    return (max(fighters or troops, key=lambda item_id: ((fighters or troops)[item_id], -item_id)),)


def family_name(sig: tuple[int, ...], static: dict[int, dict]) -> str:
    return " + ".join(static.get(item_id, {}).get("name", f"Troop {item_id}") for item_id in sig)


def read_rows(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        with path.open() as source:
            for line in source:
                if line.strip():
                    row = json.loads(line)
                    if sum(int(row[f"s{i}"]) for i in range(4)) != int(row["n"]):
                        raise ValueError(f"Stars do not sum to attacks: {row['code'][:60]}")
                    rows.append(row)
    return rows


def build(rows: list[dict], static: dict[int, dict], training_day: str,
          comparison_day: str, max_families: int = MAX_FAMILIES,
          registry: list[dict] | None = None) -> dict:
    days = {training_day, comparison_day}
    selected = [row for row in rows if row["day"] in days]
    if not selected or {row["day"] for row in selected} != days:
        raise ValueError("Both training and comparison days need outcome rows")
    by_code: dict[str, dict] = {}
    for row in selected:
        slot = by_code.setdefault(row["code"], {"n": 0})
        if row["day"] == training_day:
            slot["n"] += int(row["n"])
    for code, slot in by_code.items():
        slot["troops"], slot["setup"] = troop_housing(code, static)
    ordered = sorted(by_code, key=lambda code: (-by_code[code]["n"], code))
    families: list[dict] = []
    if registry is not None:
        if len(registry) > max_families:
            raise ValueError("Registry exceeds max families")
        for family in registry:
            families.append({**family, "signature": tuple(map(int, family["signature"])),
                             "anchors": [{int(item_id): int(amount) for item_id, amount in anchor.items()}
                                         for anchor in family["anchors"]]})
    else:
        for code in ordered:
            record = by_code[code]
            troops = record["troops"]
            if record["n"] == 0 or sum(troops.values()) < MIN_HOUSING:
                continue
            sig = signature(troops, static)
            same = next((family for family in families if family["signature"] == sig), None)
            if same:
                if len(same["anchors"]) < 8 and max(overlap(troops, anchor) for anchor in same["anchors"]) < MIN_OVERLAP:
                    same["anchors"].append(troops)
                continue
            if len(families) >= max_families:
                break
            family_id = hashlib.sha256(code.encode()).hexdigest()[:12]
            families.append({"id": family_id, "name": family_name(sig, static),
                             "signature": sig, "anchors": [troops], "representativeShareCode": code})
    assignments: dict[str, str | None] = {}
    for code, record in by_code.items():
        troops = record["troops"]
        if sum(troops.values()) < MIN_HOUSING:
            assignments[code] = None
            continue
        candidates = [(max(overlap(troops, anchor) for anchor in family["anchors"]), family["id"])
                      for family in families
                      if all(troops.get(item_id, 0) >= 0.10 * sum(troops.values())
                             for item_id in family["signature"])]
        score, family_id = max(candidates, default=(0.0, ""))
        assignments[code] = family_id if score >= MIN_OVERLAP else None
    totals: dict[tuple[str, str | None], collections.Counter] = collections.defaultdict(collections.Counter)
    setups: dict[tuple[str, str, tuple[int, ...]], int] = collections.defaultdict(int)
    for row in selected:
        family_id = assignments[row["code"]]
        point = totals[(row["day"], family_id)]
        point["attackCount"] += int(row["n"])
        for stars in range(4):
            point[f"{stars}StarCount"] += int(row[f"s{stars}"])
        point["destructionPercentageSum"] += int(row["destruction"])
        point["durationSecondsSum"] += int(row["duration"])
        if family_id is not None:
            setups[(row["day"], family_id, by_code[row["code"]]["setup"])] += int(row["n"])
    output = []
    for day in sorted(days):
        day_total = sum(stats["attackCount"] for (date, _), stats in totals.items() if date == day)
        ranks = sorted((key for key in totals if key[0] == day and key[1] is not None),
                       key=lambda key: (-totals[key]["attackCount"], key[1]))
        for rank, key in enumerate(ranks, 1):
            family_id = key[1]
            stat = totals[key]
            variants = sorted(((setup, n) for (date, fid, setup), n in setups.items()
                               if date == day and fid == family_id), key=lambda item: (-item[1], item[0]))
            output.append({"day": day, "familyId": family_id,
                           "name": next(f["name"] for f in families if f["id"] == family_id),
                           "rank": rank, "attackCount": stat["attackCount"],
                           "threeStarCount": stat["3StarCount"],
                           "threeStarRate": round(stat["3StarCount"] / stat["attackCount"], 4),
                           "usageShare": round(stat["attackCount"] / day_total, 4),
                           "setupVariants": [{"setupIds": list(setup), "attackCount": n}
                                             for setup, n in variants if n >= max(100, .05 * stat["attackCount"])][:3],
                           "storedDaily": dict(stat)})
    prior_rank = {point["familyId"]: point["rank"] for point in output if point["day"] == training_day}
    for point in output:
        if point["day"] == comparison_day:
            point["priorDayRank"] = prior_rank.get(point["familyId"])
            point["rankChange"] = (point["priorDayRank"] - point["rank"]
                                   if point["priorDayRank"] is not None else None)
    return {"prototype": "troop-overlap-v1", "trainingDay": training_day,
            "comparisonDay": comparison_day, "threshold": MIN_OVERLAP,
            "familyCount": len(families), "families": families, "daily": output,
            "review": [{"day": day, **dict(totals[(day, None)])} for day in sorted(days)],
            "sampleAttackCount": sum(int(row["n"]) for row in selected)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--training-day", required=True)
    parser.add_argument("--comparison-day", required=True)
    parser.add_argument("--max-families", type=int, default=MAX_FAMILIES)
    parser.add_argument("--registry", type=Path, help="Earlier output JSON whose family identities must stay frozen")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.max_families <= MAX_FAMILIES:
        parser.error(f"--max-families must be between 1 and {MAX_FAMILIES}")
    result = build(read_rows(args.input), load_static(args.static),
                   args.training_day, args.comparison_day, args.max_families,
                   json.loads(args.registry.read_text())["families"] if args.registry else None)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
