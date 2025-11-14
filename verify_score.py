import os
import json
import requests
import sys

THRESHOLD = 110

# Read score file
score_file = "pqi_score.json"
with open(score_file, "r") as f:
    score_data = json.load(f)

score = float(score_data["score"])

# env vars
commit_sha = os.getenv("TARGET_SHA")
repo = os.getenv("TARGET_REPO")
token = os.getenv("GH_TOKEN")


def send_status(state, description):
    url = f"https://api.github.com/repos/{repo}/statuses/{commit_sha}"
    payload = {
        "state": state,
        "context": "performance-check",
        "description": description
    }
    headers = {"Authorization": f"token {token}"}
    r = requests.post(url, json=payload, headers=headers)
    print("GitHub Status Response:", r.text)


if score < THRESHOLD:
    print(f"❌ Performance Failed: {score} < {THRESHOLD}")
    send_status("failure", f"Performance score too low ({score})")
    sys.exit(1)
else:
    print(f"✅ Performance Passed: {score} >= {THRESHOLD}")
    send_status("success", f"Performance score OK ({score})")
    sys.exit(0)
