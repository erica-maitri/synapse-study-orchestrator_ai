import sys
import os
import json
import argparse

# Import the skills directly
from skills.spaced_repetition.sm2 import calculate_next_review
from skills.task_scoring.score import calculate_priority_score

SKILLS_DIR = os.path.dirname(os.path.abspath(__file__))

def load_manifest(skill_name: str) -> dict:
    manifest_path = os.path.join(SKILLS_DIR, skill_name, "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r") as f:
        return json.load(f)

def list_skills():
    print("\n=== Synapse Registered Skills ===")
    skills = ["spaced_repetition", "task_scoring"]
    for skill in skills:
        manifest = load_manifest(skill)
        if manifest:
            print(f"\nSkill: {manifest['name']}")
            print(f"Description: {manifest['description']}")
            print("Inputs:")
            for inp, details in manifest["inputs"].items():
                req = "required" if details["required"] else "optional"
                print(f"  - {inp} ({details['type']}): {details['description']} [{req}]")
            print("Outputs:")
            for out, otype in manifest["outputs"].items():
                print(f"  - {out}: {otype}")
    print("\n=================================")

def run_skill_with_args(args):
    skill_name = args.name
    
    # Prepare parameters from either --args (JSON) or direct command flags
    params = {}
    if args.args:
        try:
            params = json.loads(args.args)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON argument string: {args.args}")
            sys.exit(1)
    else:
        # Extract direct CLI options
        direct_args = ["quality", "repetitions", "ease_factor", "interval", "importance", "urgency", "due_date"]
        for key in direct_args:
            val = getattr(args, key)
            if val is not None:
                params[key] = val

    if skill_name == "spaced_repetition":
        # Handle legacy parameter mapping from interval_days to interval if needed
        if "interval_days" in params and "interval" not in params:
            params["interval"] = params["interval_days"]

        required = ["quality", "repetitions", "ease_factor", "interval"]
        for r in required:
            if r not in params:
                print(f"Error: Missing required argument '{r}' for spaced_repetition.")
                print("Provide either --args '<json_str>' or directly: --quality, --repetitions, --ease_factor, --interval")
                sys.exit(1)
        try:
            result = calculate_next_review(
                quality=int(params["quality"]),
                repetitions=int(params["repetitions"]),
                ease_factor=float(params["ease_factor"]),
                interval=int(params["interval"])
            )
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Execution Error: {e}")
            sys.exit(1)
            
    elif skill_name == "task_scoring":
        required = ["importance", "urgency"]
        for r in required:
            if r not in params:
                print(f"Error: Missing required argument '{r}' for task_scoring.")
                print("Provide either --args '<json_str>' or directly: --importance, --urgency, and optionally --due_date")
                sys.exit(1)
        try:
            result = calculate_priority_score(
                importance=int(params["importance"]),
                urgency=int(params["urgency"]),
                due_date=params.get("due_date")
            )
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Execution Error: {e}")
            sys.exit(1)
    else:
        print(f"Error: Unknown skill name '{skill_name}'")
        sys.exit(1)

def main():
    # Strip out 'skills' if it's passed as the first argument,
    # converting `synapse skills run ...` into `run ...` for argparse.
    args_list = sys.argv[1:]
    if args_list and args_list[0] == "skills":
        args_list = args_list[1:]

    parser = argparse.ArgumentParser(description="Synapse Skills CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    subparsers.add_parser("list", help="List all registered skills")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a specific skill")
    run_parser.add_argument("name", type=str, help="Name of the skill to run")
    run_parser.add_argument("--args", type=str, required=False, help="JSON arguments string for the skill")
    
    # Direct flags for spaced_repetition
    run_parser.add_argument("--quality", type=int, required=False, help="Performance score (0-5)")
    run_parser.add_argument("--repetitions", type=int, required=False, help="Consecutive successful reviews")
    run_parser.add_argument("--ease_factor", type=float, required=False, help="Current ease factor (e.g. 2.5)")
    run_parser.add_argument("--interval", type=int, required=False, help="Current interval in days")
    
    # Direct flags for task_scoring
    run_parser.add_argument("--importance", type=int, required=False, help="Importance level (1-5)")
    run_parser.add_argument("--urgency", type=int, required=False, help="Urgency level (1-5)")
    run_parser.add_argument("--due_date", type=str, required=False, help="Optional task due date (YYYY-MM-DD)")

    parsed_args = parser.parse_args(args_list)

    if parsed_args.command == "list":
        list_skills()
    elif parsed_args.command == "run":
        run_skill_with_args(parsed_args)
    else:
        parser.print_help()

if __name__ == "__main__":
    # Ensure package imports work when executed directly
    sys.path.append(os.path.dirname(SKILLS_DIR))
    main()
