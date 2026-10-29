#!/usr/bin/env python3
"""Builds and validates Willow Guild capsules and registry (`PA-14` / `CRUCIBLE-06`)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

GUILD_ROOT = Path(__file__).resolve().parent.parent
VOCAB_PATH = GUILD_ROOT / "vocab" / "core_verbs.json"
SEED_PATH = GUILD_ROOT / "design" / "seed_capsules.json"
CAPSULES_DIR = GUILD_ROOT / "content" / "capsules"
REGISTRY_PATH = GUILD_ROOT / "content" / "registry.json"

REQUIRED_STAT_KEYS = ("frt", "eth", "prw", "ten", "ast", "agi")
REQUIRED_CAPSULE_KEYS = {
    "capsule_id",
    "title",
    "capsule_type",
    "slot",
    "rig_socket",
    "style_theme",
    "enclave_emotion_id",
    "cost_rupees",
    "frontier_cost",
    "stats",
    "practice_avenue",
    "mastery_ap_required",
    "ability_id",
    "flow_prompt",
    "flow_settings",
    "audio_script",
}
OPTIONAL_CAPSULE_KEYS = {
    "quest_hook",
    "dialogue_lines",
    "idle_animation_clip",
    "mood_modifiers",
    "synthesized_at_utc",
    "safety_attestation",
    "boss_mountain",
    "encounter_tier",
}


def validate_guild_capsule(capsule: dict[str, Any], vocab: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cid = str(capsule.get("capsule_id", ""))
    if not re.match(r"^willow-guild-[a-z0-9-]+$", cid):
        errors.append(f"Invalid capsule_id '{cid}': must match ^willow-guild-[a-z0-9-]+$")

    keys = set(capsule.keys())
    missing = REQUIRED_CAPSULE_KEYS - keys
    extra = keys - (REQUIRED_CAPSULE_KEYS | OPTIONAL_CAPSULE_KEYS)
    if missing or extra:
        errors.append(f"{cid}: key mismatch missing={sorted(missing)} extra={sorted(extra)}")

    if not isinstance(capsule.get("title"), str) or not capsule["title"].strip():
        errors.append(f"{cid}: missing non-empty title")

    ctype = capsule.get("capsule_type")
    if ctype not in vocab["capsule_types"]:
        errors.append(f"{cid}: invalid capsule_type '{ctype}'")

    slot = capsule.get("slot")
    slots_map = vocab["slots"]
    if slot not in slots_map:
        errors.append(f"{cid}: invalid slot '{slot}'")
    else:
        expected_socket = slots_map[slot]["rig_socket"]
        if capsule.get("rig_socket") != expected_socket:
            errors.append(
                f"{cid}: rig_socket '{capsule.get('rig_socket')}' does not match slot '{slot}' expected '{expected_socket}'"
            )

    if capsule.get("style_theme") not in vocab["style_themes"]:
        errors.append(f"{cid}: invalid style_theme '{capsule.get('style_theme')}'")

    if capsule.get("enclave_emotion_id") not in vocab["enclave_emotion_ids"]:
        errors.append(f"{cid}: invalid enclave_emotion_id '{capsule.get('enclave_emotion_id')}'")

    cost_rup = capsule.get("cost_rupees")
    if not isinstance(cost_rup, int) or not (1 <= cost_rup <= 1000):
        errors.append(f"{cid}: cost_rupees '{cost_rup}' outside [1, 1000]")

    f_cost = capsule.get("frontier_cost")
    if not isinstance(f_cost, int) or not (1 <= f_cost <= 100):
        errors.append(f"{cid}: frontier_cost '{f_cost}' outside [1, 100]")

    stats = capsule.get("stats")
    if not isinstance(stats, dict):
        errors.append(f"{cid}: stats must be an object")
    else:
        for sk in REQUIRED_STAT_KEYS:
            val = stats.get(sk)
            if not isinstance(val, int) or val < 0:
                errors.append(f"{cid}: stats.{sk} must be a non-negative integer")

    raw_av = capsule.get("practice_avenue")
    av_id = raw_av.get("avenue_id") if isinstance(raw_av, dict) else raw_av
    if av_id not in vocab["practice_avenues"]:
        errors.append(f"{cid}: invalid practice_avenue '{raw_av}'")

    ap_req = capsule.get("mastery_ap_required")
    if not isinstance(ap_req, int) or not (50 <= ap_req <= 500):
        errors.append(f"{cid}: mastery_ap_required '{ap_req}' outside [50, 500]")

    veo_contract = vocab["veo_31_prompt_contract"]
    prompt = capsule.get("flow_prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        errors.append(f"{cid}: missing flow_prompt")
    else:
        words = [w for w in re.split(r"\s+", prompt.strip()) if w]
        w_min = veo_contract["word_count_min"]
        w_max = veo_contract["word_count_max"]
        if not (w_min <= len(words) <= w_max):
            errors.append(f"{cid}: flow_prompt word count {len(words)} outside [{w_min}, {w_max}]")
        forbidden_re = re.compile(veo_contract["forbidden_overlay_regex"], re.IGNORECASE)
        m = forbidden_re.search(prompt)
        if m:
            errors.append(
                f"{cid}: flow_prompt contains forbidden Veo 3.1 text-overlay trigger '{m.group(0)}'"
            )
        if "Audio:" not in prompt or "no background music" not in prompt.lower():
            errors.append(f"{cid}: flow_prompt must include 'Audio:' and 'no background music'")

    f_settings = capsule.get("flow_settings")
    if not isinstance(f_settings, dict):
        errors.append(f"{cid}: missing flow_settings object")
    else:
        for req_k, req_v in veo_contract["required_flow_settings"].items():
            if f_settings.get(req_k) != req_v:
                errors.append(
                    f"{cid}: flow_settings.{req_k}='{f_settings.get(req_k)}' != '{req_v}'"
                )

    a_script = capsule.get("audio_script")
    if not isinstance(a_script, dict):
        errors.append(f"{cid}: missing audio_script object")
    else:
        if a_script.get("speech_mode") not in veo_contract["allowed_speech_modes"]:
            errors.append(f"{cid}: invalid audio_script.speech_mode '{a_script.get('speech_mode')}'")
        if a_script.get("target_lufs") not in veo_contract["allowed_target_lufs"]:
            errors.append(f"{cid}: invalid audio_script.target_lufs '{a_script.get('target_lufs')}'")

    return errors


validate_capsule_dict = validate_guild_capsule


def build_or_check(check_only: bool = False) -> int:
    vocab = json.loads(VOCAB_PATH.read_text(encoding="utf-8"))
    seed_doc = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    seed_capsules = seed_doc.get("capsules", [])

    CAPSULES_DIR.mkdir(parents=True, exist_ok=True)
    all_errors: list[str] = []
    registry_entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for cap in seed_capsules:
        errs = validate_guild_capsule(cap, vocab)
        all_errors.extend(errs)
        cid = cap["capsule_id"]
        seen_ids.add(cid)
        target_file = CAPSULES_DIR / f"{cid}.json"
        rendered = json.dumps(cap, indent=2, sort_keys=False) + "\n"
        sha256 = hashlib.sha256(rendered.encode("utf-8")).hexdigest()

        if check_only:
            if not target_file.is_file():
                all_errors.append(f"Missing materialized capsule file: {target_file}")
            elif target_file.read_text(encoding="utf-8") != rendered:
                all_errors.append(f"Out-of-sync capsule file: {target_file}")
        else:
            target_file.write_text(rendered, encoding="utf-8")

        registry_entries.append(
            {
                "capsule_id": cid,
                "title": cap["title"],
                "capsule_type": cap["capsule_type"],
                "slot": cap["slot"],
                "rig_socket": cap["rig_socket"],
                "style_theme": cap["style_theme"],
                "enclave_emotion_id": cap["enclave_emotion_id"],
                "cost_rupees": cap["cost_rupees"],
                "frontier_cost": cap["frontier_cost"],
                "practice_avenue": cap["practice_avenue"],
                "mastery_ap_required": cap["mastery_ap_required"],
                "ability_id": cap.get("ability_id", ""),
                "encounter_tier": cap.get("encounter_tier", cap["capsule_type"]),
                "file": f"content/capsules/{cid}.json",
                "path": f"content/capsules/{cid}.json",
                "sha256": sha256,
            }
        )

    # Also validate and register any additional willow-guild-*.json files in content/capsules/
    seed_ids = {c["capsule_id"] for c in seed_capsules}
    for extra_path in sorted(CAPSULES_DIR.glob("willow-guild-*.json")):
        if extra_path.stem in seed_ids:
            continue
        try:
            extra_raw = extra_path.read_text(encoding="utf-8")
            extra_cap = json.loads(extra_raw)
        except Exception as exc:
            all_errors.append(f"{extra_path.name}: invalid JSON ({exc})")
            continue
        errs = validate_guild_capsule(extra_cap, vocab)
        all_errors.extend(errs)
        if errs:
            continue
        cid = str(extra_cap.get("capsule_id") or extra_path.stem)
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        rendered_extra = json.dumps(extra_cap, indent=2, sort_keys=False) + "\n"
        if not check_only and extra_raw != rendered_extra:
            extra_path.write_text(rendered_extra, encoding="utf-8")
            extra_raw = rendered_extra
        extra_sha256 = hashlib.sha256(extra_raw.encode("utf-8")).hexdigest()
        raw_av = extra_cap.get("practice_avenue", "vanguard")
        av_id = raw_av.get("avenue_id", "vanguard") if isinstance(raw_av, dict) else str(raw_av)
        bm = extra_cap.get("boss_mountain")
        enc_tier = (
            bm.get("encounter_tier", "guild_patrol")
            if isinstance(bm, dict)
            else str(extra_cap.get("encounter_tier") or extra_cap.get("capsule_type") or "guild_patrol")
        )
        registry_entries.append(
            {
                "capsule_id": cid,
                "title": extra_cap["title"],
                "capsule_type": extra_cap.get("capsule_type", "wardrobe_gear"),
                "slot": extra_cap["slot"],
                "rig_socket": extra_cap["rig_socket"],
                "style_theme": extra_cap["style_theme"],
                "enclave_emotion_id": extra_cap["enclave_emotion_id"],
                "cost_rupees": extra_cap["cost_rupees"],
                "frontier_cost": extra_cap["frontier_cost"],
                "practice_avenue": av_id,
                "mastery_ap_required": extra_cap["mastery_ap_required"],
                "ability_id": extra_cap.get("ability_id", ""),
                "encounter_tier": enc_tier,
                "file": f"content/capsules/{extra_path.name}",
                "path": f"content/capsules/{extra_path.name}",
                "sha256": extra_sha256,
            }
        )

    registry_doc = {
        "schema": "lfs-willow-guild-registry-v1",
        "project_id": "PA-14",
        "capsule_id": "willow-desktop-pet",
        "total_capsules": len(registry_entries),
        "capsule_count": len(registry_entries),
        "capsules": registry_entries,
    }
    rendered_reg = json.dumps(registry_doc, indent=2) + "\n"

    if check_only:
        if not REGISTRY_PATH.is_file():
            all_errors.append(f"Missing registry file: {REGISTRY_PATH}")
        elif REGISTRY_PATH.read_text(encoding="utf-8") != rendered_reg:
            all_errors.append(f"Out-of-sync registry file: {REGISTRY_PATH}")
    else:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(rendered_reg, encoding="utf-8")

    if all_errors:
        for e in all_errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(
        f"WILLOW_GUILD_REGISTRY_OK: {len(registry_entries)} capsules validated (Veo 3.1 Anti-Overlay Gate PASS)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or check Willow Guild capsule registry.")
    parser.add_argument("--check", action="store_true", help="Verify existing files without writing.")
    args = parser.parse_args()
    return build_or_check(check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
