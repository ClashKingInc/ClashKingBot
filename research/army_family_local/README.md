# Army family local prototype

This is an offline research script. It reads the already-exported Army Lab day files and pinned Clash static metadata. It has no database or network code, no scheduler, and no production write path. It did not modify the existing Army Lab experiment.

The initial day's attack-weighted share codes seed at most 48 families. Only main-army troop housing enters the 80% overlap score; small support units are removed, spells and equipment do not affect family assignment, and incomplete armies go to review. Families with the same major fighting troop signature share one name and up to eight reference armies. The first reference code gives a deterministic local ID. A later run can load the previous output with `--registry` to freeze IDs, names, and references; unmatched codes stay in review until someone explicitly promotes or revises a family. The rank is by attacks within the sampled day, and `rankChange` is prior rank minus current rank.

The optional `setupVariants` are the two or three most common exact equipment plus 3-or-more spell signatures above a 5% and 100-attack floor. They are descriptive children of a troop family; the prototype does not assert that a setup improves its hit rate. Every daily family row also includes attack count, all star counts, three-star rate, usage share, destruction sum, and duration sum.

Run from this directory:

```sh
python3 -m unittest test_prototype.py
python3 prototype.py \
  --input /Users/matthewanderson/Documents/Codex/2026-09-09/can/work/army-research/lab-outcomes/2026-09-18.jsonl /Users/matthewanderson/Documents/Codex/2026-09-09/can/army-lab/research/recent/20260920T171858Z/2026-09-19.jsonl \
  --static /Users/matthewanderson/go/pkg/mod/github.com/clashkinginc/clashy.go@v0.1.15-0.20260901045716-ed49cb54e8ea/static/static_data.json \
  --training-day 2026-09-18 --comparison-day 2026-09-19 --output sample-output.json
```

The checked-in output contains 79,384 September 18 attacks and 78,069 September 19 attacks. It found 48 families, leaving 470 and 495 attacks respectively for review. On September 19, Thrower ranked first with 21,827 attacks and 11,319 three-star attacks (51.86%); Super Bowler rose from rank 3 to 2 with 15,946 attacks (43.11% three-star); Dragon + Dragon Rider fell from rank 2 to 3 with 15,631 attacks (49.01% three-star). These are descriptive results from a previously exported Legend sample, not live or deployed stats. The source's 05:10 UTC day boundary and population rules remain those of Army Lab.

## Proposed durable shape

The authoritative `clashking_schemas/database/timescale/017_final_operational_contract.sql` already defines `army_families`, `army_family_members`, and `army_family_daily_stats`. A production implementation should map reviewed local identities to the schema's `bigint family_id`, preserve a representative share code and normalized name in `army_families`, and assign each canonical code in `army_family_members`. The daily row uses `(day, cohort, family_id)` as its key and stores `attack_count`, `distinct_player_count`, four star counts, `destruction_percentage_sum`, and `duration_seconds_sum`. Current cohorts are `legend_i`, `top_1000`, and `top_200`; the Army Lab export does not retain player identities or separate cohort rows, so its output cannot populate `distinct_player_count` or be copied into that table unchanged.

For example, the prototype's leading September 19 family has this *partial* daily payload, pending reviewed ID/cohort mapping and distinct-player aggregation:

```json
{
  "day": "2026-09-19",
  "localFamilyId": "8f6b57e6b72e",
  "attackCount": 21827,
  "zeroStarCount": 15,
  "oneStarCount": 2878,
  "twoStarCount": 7615,
  "threeStarCount": 11319,
  "destructionPercentageSum": 2026062,
  "durationSecondsSum": 3406196
}
```

Usage share and rank should be derived from the cohort's `legend_daily_stats.attack_count` and ordered family daily rows. The optional setup variants need a separate reviewed child identity and daily table if retained; they do not belong in the existing family aggregate. The local output's anchor vectors and prototype IDs are research data, not a migration or a proposed public API shape.

The main unresolved quality question is whether the 48 named groups align with player-recognized strategies. The prototype has no independent human validation, and 80% overlap can still merge tactical differences or split a real family. Freeze and review family identities before any durable write or UI rollout.
