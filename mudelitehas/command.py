"""Parse the shared Estonian Mudelitehas request; no generation side effects."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent

def parse_command(command):
    command = command.strip()
    match = re.fullmatch(r"Mudelitehas\s+(\d+)\s+([123])\s+(.+)", command, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("Kasuta kuju: Mudelitehas <nelinurkade_arv> <1|2|3> <mudeli kirjeldus>")
    faces, level, description = int(match[1]), int(match[2]), " ".join(match[3].split())
    if faces < 4:
        raise ValueError("Nelinurkade arv peab olema vähemalt 4.")
    profiles = json.loads((ROOT / "profiles.json").read_text(encoding="utf-8"))
    animation_requested = bool(re.search(r"\b\w*animatsiooniga\b|\banimatsioon\s*=", description, re.IGNORECASE))
    return {
        "schema_version": 1,
        "command": f"Mudelitehas {faces} {level} {description}",
        "quad_faces": faces,
        "level": level,
        "description": description,
        "animation_requested": animation_requested,
        "budget_scope": profiles["budget_scope"],
        "pipeline": profiles["shared_pipeline"],
        "profile": profiles["levels"][str(level)],
        "needs_prepared_reference_images": True,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = parse_command(args.command)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")

if __name__ == "__main__":
    main()
