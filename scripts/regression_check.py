"""
Regression check — run before merging any change to search_agent.py or ranking_agent.py.
All checks must pass before pushing to main.

Usage: .venv/bin/python scripts/regression_check.py
"""
import os, sys, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from config import AUTODEV_API_KEY

PASS = "✅"
FAIL = "❌"
headers = {"Authorization": f"Bearer {AUTODEV_API_KEY}"}

CHECKS = [
    # (make, model, zip, min_expected_results, description)
    ("Honda",   "CR-V",     "92782", 100, "Honda CR-V near 92782"),
    ("Toyota",  "RAV4",     "92782", 100, "Toyota RAV4 near 92782"),
    ("BMW",     "X5",       "92782", 100, "BMW X5 near 92782"),
    ("Ford",    "F-150",    "92782",  50, "Ford F-150 near 92782"),
    ("Jeep",    "Wrangler", "92782",  50, "Jeep Wrangler near 92782"),
    ("Lexus",   "TX",       "92782",   1, "Lexus TX near 92782 (low inventory ok)"),
]

results = []
print("\nRunning live API regression checks...\n")
print(f"{'Check':<40} {'Count':<10} {'Status'}")
print("─" * 65)

for make, model, zip_, min_count, desc in CHECKS:
    try:
        r = requests.get(
            "https://auto.dev/api/listings",
            headers=headers,
            params={"make": make, "model": model, "zip": zip_, "radius": 50, "per_page": 1},
            timeout=15,
        )
        if r.status_code != 200:
            count, ok = 0, False
            status = f"{FAIL} HTTP {r.status_code}"
        else:
            count = r.json().get("totalCount", 0) or 0
            ok = count >= min_count
            status = f"{PASS} {count:,} results" if ok else f"{FAIL} {count} results (need ≥{min_count})"
    except Exception as e:
        ok, status = False, f"{FAIL} ERROR: {e}"
    print(f"{desc:<40} {status}")
    results.append(ok)

print("─" * 65)
passed = sum(results)
total = len(results)
print(f"\n{PASS if passed == total else FAIL} {passed}/{total} checks passed\n")
sys.exit(0 if passed == total else 1)
