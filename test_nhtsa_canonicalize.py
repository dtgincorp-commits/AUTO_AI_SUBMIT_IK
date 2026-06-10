"""
Regression test for agents/nhtsa.py canonicalize_model.

Two layers:
1. Targeted cases — real bugs seen in production (LangSmith traces):
   - "audi rs3" was canonicalized to "S3" (substring trap: s3 ⊂ rs3)
   - "GLS 600" was canonicalized to "600" (NHTSA's historical Mercedes "600"
     matched in reverse inside "gls600")
2. Full sweep — every NHTSA model for every supported make, fed back in as
   user-style variants (lowercased, space-stripped). Each must round-trip to
   the exact NHTSA name. Known NHTSA data ambiguities (duplicate official
   entries, all Honda motorcycles) are whitelisted.

Runs offline against .nhtsa_cache.json (refreshes weekly via the agent).
"""
from agents.nhtsa import SUPPORTED_MAKES, get_models_for_make, canonicalize_model

# NHTSA itself contains duplicate entries for these (e.g. both "Silverwing"
# and "Silver Wing" exist as separate official rows) — ambiguity in their
# data, not a matching bug. All are Honda motorcycles, irrelevant to the app.
KNOWN_NHTSA_DUPLICATES = {
    ("Honda", "silverwing"),
    ("Honda", "silver wing"),
    ("Honda", "rc45"),
    ("Honda", "rc 45"),
}

TARGETED = [
    # (make, user input, expected canonical)
    ("Audi",          "rs3",      "RS 3"),
    ("Audi",          "RS3",      "RS 3"),
    ("Audi",          "rs7",      "RS 7"),
    ("Audi",          "ttrs",     "TT RS"),
    ("Audi",          "S3",       "S3"),       # must NOT get hijacked by RS 3
    ("Mercedes-Benz", "GLS 600",  "GLS 600"),  # must NOT collapse to "600"
    ("Mercedes-Benz", "GLS",      "GLS-Class"),
    ("BMW",           "M340i",    "M340i"),    # not in NHTSA — pass through
    ("BMW",           "X5",       "X5"),
    ("Toyota",        "RAV4",     "RAV4"),
    ("Honda",         "CR-V",     "CR-V"),
    ("Lexus",         "GX 550",   "GX 550"),
]


def run() -> bool:
    ok = True

    print("Targeted cases:")
    for make, typed, want in TARGETED:
        got = canonicalize_model(make, typed)
        mark = "✅" if got == want else "❌"
        if got != want:
            ok = False
        print(f"  {mark} {make} '{typed}' → '{got}' (expected '{want}')")

    print("\nFull sweep (every NHTSA model, user-style variants):")
    total, fails = 0, []
    for make in SUPPORTED_MAKES:
        for m in get_models_for_make(make):
            for v in {m.lower(), m.replace(" ", ""), m.replace(" ", "").lower()}:
                if (make, v.lower()) in KNOWN_NHTSA_DUPLICATES:
                    continue
                total += 1
                got = canonicalize_model(make, v)
                if got != m:
                    fails.append((make, v, got, m))

    for make, v, got, want in fails[:20]:
        print(f"  ❌ {make} '{v}' → '{got}' (expected '{want}')")
    if fails:
        ok = False
    print(f"  {total - len(fails)}/{total} variants round-trip correctly")

    print(f"\n{'✅ PASS' if ok else '❌ FAIL'}")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
