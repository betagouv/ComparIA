import json
from pathlib import Path

MODELS_PATH = Path("utils/models/models.json")

def fix_models_json():
    with open(MODELS_PATH, "r") as f:
        data = json.load(f)

    orgs = []
    orphans = []
    google_org = None

    for item in data:
        if "models" in item:
            orgs.append(item)
            if item.get("name") == "Google":
                google_org = item
        else:
            orphans.append(item)

    if not google_org:
        print("Google organization not found!")
        return

    if orphans:
        print(f"Found {len(orphans)} orphaned models. Moving them to Google organization.")
        google_org["models"].extend(orphans)
    else:
        print("No orphaned models found.")

    with open(MODELS_PATH, "w") as f:
        json.dump(orgs, f, indent=2, ensure_ascii=False)
        f.write("\n") # Add trailing newline

if __name__ == "__main__":
    fix_models_json()
