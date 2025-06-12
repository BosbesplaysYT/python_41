import os
import json

CONFIG_PATH = os.path.expanduser("~/.nexus_editor/config.json")


def is_first_launch():
    if not os.path.exists(CONFIG_PATH):
        return True
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        return not data.get("launched_before", False)
    except Exception:
        return True


def mark_launched():
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"launched_before": True}, f)
