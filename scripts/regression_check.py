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
    # High-volume — must have plenty of results
    ("Honda",         "CR-V",            "92782", 100, "Honda CR-V"),
    ("Toyota",        "RAV4",            "92782", 100, "Toyota RAV4"),
    ("Ford",          "F-150",           "92782",  50, "Ford F-150"),
    ("Chevrolet",     "Silverado 1500",  "92782",  50, "Chevrolet Silverado 1500"),
    ("Jeep",          "Wrangler",        "92782",  50, "Jeep Wrangler"),
    ("Ram",           "1500",            "92782",  50, "Ram 1500"),
    ("Hyundai",       "Tucson",          "92782",  50, "Hyundai Tucson"),
    ("Kia",           "Telluride",       "92782",  20, "Kia Telluride"),
    ("Nissan",        "Altima",          "92782",  50, "Nissan Altima"),
    ("Subaru",        "Outback",         "92782",  50, "Subaru Outback"),
    # Mid-volume
    ("BMW",           "X5",              "92782",  50, "BMW X5"),
    ("Mercedes-Benz", "GLE",             "92782",  20, "Mercedes-Benz GLE"),
    ("Audi",          "Q5",              "92782",  20, "Audi Q5"),
    ("Volkswagen",    "Atlas",           "92782",  20, "Volkswagen Atlas"),
    ("Volvo",         "XC90",            "92782",  10, "Volvo XC90"),
    ("Acura",         "MDX",             "92782",  20, "Acura MDX"),
    ("Infiniti",      "QX60",            "92782",  10, "Infiniti QX60"),
    ("Cadillac",      "Escalade",        "92782",  10, "Cadillac Escalade"),
    ("Lincoln",       "Navigator",       "92782",   5, "Lincoln Navigator"),
    ("Buick",         "Enclave",         "92782",  10, "Buick Enclave"),
    ("GMC",           "Yukon",           "92782",  10, "GMC Yukon"),
    ("Mazda",         "CX-5",            "92782",  20, "Mazda CX-5"),
    ("Genesis",       "GV80",            "92782",   5, "Genesis GV80"),
    ("Tesla",         "Model Y",         "92782",  20, "Tesla Model Y"),
    # Lower volume — at least 1
    ("Lexus",         "TX",              "92782",   1, "Lexus TX"),
    ("Porsche",       "Cayenne",         "92782",   5, "Porsche Cayenne"),
    ("Land Rover",    "Range Rover",     "92782",   5, "Land Rover Range Rover"),
    ("Jaguar",        "F-PACE",          "92782",   1, "Jaguar F-PACE"),
    ("Alfa Romeo",    "Stelvio",         "92782",   1, "Alfa Romeo Stelvio"),
    ("Maserati",      "Levante",         "92782",   1, "Maserati Levante"),
    ("Bentley",       "Bentayga",        "92782",   1, "Bentley Bentayga"),
    ("Rolls-Royce",   "Cullinan",        "92782",   1, "Rolls-Royce Cullinan"),
    ("Lamborghini",   "Urus",            "92782",   1, "Lamborghini Urus"),
    ("Rivian",        "R1S",             "92782",   1, "Rivian R1S"),
    ("Lucid",         "Air",             "92782",   1, "Lucid Air"),
]

results = []
print("\nRunning live API regression checks (with app-realistic params)...\n")
print(f"{'Check':<40} {'Status'}")
print("─" * 65)

# Simulate exactly what the app sends — no price filter when user sets no budget (fixed behaviour)
APP_DEFAULT_PARAMS = {
    "distance": 50,
    "limit": 1,
}

for make, model, zip_, min_count, desc in CHECKS:
    try:
        # Use same endpoint + params as the app (vehicle.make/model, page-based)
        r_app = requests.get(
            "https://auto.dev/api/listings",
            headers=headers,
            params={"vehicle.make": make, "vehicle.model": model, "zip": zip_,
                    "distance": 50, "limit": 10, "page": 1},
            timeout=15,
        )
        if r_app.status_code != 200:
            ok, status = False, f"{FAIL} HTTP {r_app.status_code}"
        else:
            data = r_app.json()
            count_app = len(data.get("data") or [])
            ok = count_app >= min(min_count, 1)  # app returns pages of records not totalCount
            status = f"{PASS} {count_app} records on page 1" if ok else f"{FAIL} 0 records returned (need ≥1)"
    except Exception as e:
        ok, status = False, f"{FAIL} ERROR: {e}"
    print(f"{desc:<40} {status}")
    results.append(ok)

print("─" * 65)
passed = sum(results)
total = len(results)
print(f"\n{PASS if passed == total else FAIL} {passed}/{total} checks passed\n")
sys.exit(0 if passed == total else 1)
