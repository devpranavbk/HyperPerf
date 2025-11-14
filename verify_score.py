import json
import sys

SCORE_THRESHOLD = 110  # Required score for merge

try:
    with open("score_output.json", "r") as f:
        data = json.load(f)
        score = float(data["pqi_score"])
except Exception as e:
    print("❌ Could not read score_output.json:", e)
    sys.exit(1)

print(f"🔍 PQI Score Read: {score}")

if score < SCORE_THRESHOLD:
    print(f"❌ Performance too low. Score = {score}, Threshold = {SCORE_THRESHOLD}")
    print("⛔ Blocking merge (exiting with failure code)")
    sys.exit(1)

print("✅ Performance score acceptable. Proceed with merge.")
sys.exit(0)
