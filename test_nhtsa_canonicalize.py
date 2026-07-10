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
from agents.nhtsa import SUPPORTED_MAKES, get_models_for_make, canonicalize_model, split_model_trim

# split_model_trim(make, model) -> (canonical_model, trim). Locks the model↔trim
# boundary that caused the "gt63" incident (searched "AMG GT 63" → 0 results
# because the DB stores model "AMG GT" + trim "63"). Word-boundary rule must:
#   - peel real variants (AMG GT 63, CT5 V, 911 Turbo S)
#   - NOT peel mid-token (M340i must stay M340i, never "M3"+"40i")
#   - NOT peel end-of-string coincidences (GLS 600 stays whole)
SPLIT_CASES = [
    # (make, input, expected_model, expected_trim)
    ("Mercedes-Benz", "AMG GT 63", "AMG GT",   "63"),
    ("Mercedes-Benz", "AMG GT 53", "AMG GT",   "53"),
    ("Mercedes-Benz", "GLS 600",   "GLS 600",  ""),    # coincidence: 600 at END
    ("BMW",           "M340i",     "M340i",    ""),    # trap: must NOT become M3
    ("BMW",           "M3",        "M3",       ""),
    ("Cadillac",      "CT5 V",     "CT5",      "V"),
    ("Porsche",       "911 Turbo S", "911",    "Turbo S"),
    ("Audi",          "RS3",       "RS 3",     ""),    # whole model
    ("BMW",           "X5",        "X5",       ""),
    # NOTE: split_model_trim DOES peel "GX 550" → ("GX","550"); Lexus is protected
    # a layer up by the fallback-on-zero probe (GX 550 returns results → no
    # switch). canonicalize_model (parse-time) keeps "GX 550" whole — tested above.
]

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

    print("\nModel↔trim split (the gt63 incident — locks the boundary):")
    for make, typed, exp_model, exp_trim in SPLIT_CASES:
        gm, gt = split_model_trim(make, typed)
        mark = "✅" if (gm, gt) == (exp_model, exp_trim) else "❌"
        if (gm, gt) != (exp_model, exp_trim):
            ok = False
        print(f"  {mark} {make} '{typed}' → model={gm!r} trim={gt!r} (want {exp_model!r},{exp_trim!r})")

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
