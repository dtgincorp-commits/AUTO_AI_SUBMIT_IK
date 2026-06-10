"""
NHTSA vPIC — canonical make/model source.

Fetches all models for supported makes from the US government vehicle database.
Results are cached locally in .nhtsa_cache.json and refreshed weekly.
No API key required.
"""
import json
import os
import re
import time
import requests
from typing import Dict, List, Optional

_CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", ".nhtsa_cache.json")
_CACHE_TTL  = 7 * 24 * 3600   # 1 week

SUPPORTED_MAKES = [
    "Acura", "Alfa Romeo", "Aston Martin", "Audi", "Bentley", "BMW",
    "Buick", "Cadillac", "Chevrolet", "Chrysler", "Dodge", "Ferrari",
    "Ford", "Genesis", "GMC", "Honda", "Hyundai", "Infiniti", "Jaguar",
    "Jeep", "Kia", "Lamborghini", "Land Rover", "Lexus", "Lincoln",
    "Lucid", "Maserati", "Mazda", "Mercedes-Benz", "Mitsubishi", "Nissan",
    "Porsche", "RAM", "Rivian", "Rolls-Royce", "Subaru", "Tesla",
    "Toyota", "Volkswagen", "Volvo",
]

_BASE = "https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{}?format=json"


def _fetch_make(make: str) -> List[str]:
    try:
        r = requests.get(_BASE.format(requests.utils.quote(make)), timeout=10)
        r.raise_for_status()
        return [x["Model_Name"] for x in r.json().get("Results", [])]
    except Exception:
        return []


def _load_cache() -> Optional[dict]:
    try:
        with open(_CACHE_FILE) as f:
            data = json.load(f)
        if time.time() - data.get("_ts", 0) < _CACHE_TTL:
            return data
    except Exception:
        pass
    return None


def _save_cache(data: dict):
    try:
        data["_ts"] = time.time()
        with open(_CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def get_all_models() -> Dict[str, List[str]]:
    """Return {make: [model, ...]} for all supported makes. Uses cache."""
    cached = _load_cache()
    if cached:
        return {k: v for k, v in cached.items() if k != "_ts"}

    result = {}
    for make in SUPPORTED_MAKES:
        models = _fetch_make(make)
        result[make] = models
        time.sleep(0.05)   # gentle on the API

    _save_cache(result)
    return result


def get_models_for_make(make: str) -> List[str]:
    """Return model list for a single make. Uses full cache."""
    all_models = get_all_models()
    # Try exact match first, then case-insensitive
    if make in all_models:
        return all_models[make]
    for k, v in all_models.items():
        if k.lower() == make.lower():
            return v
    # Not in cache — fetch live
    return _fetch_make(make)


def canonicalize_model(make: str, model: str) -> str:
    """
    Return the NHTSA-canonical model name for a given make+model string.
    Matches case-insensitively. Returns original string if no match found.
    """
    models = get_models_for_make(make)
    model_lower = model.lower().strip()
    # Collapse internal whitespace so "rs3" matches NHTSA's "RS 3"
    model_compact = re.sub(r'\s+', '', model_lower)
    for m in models:
        if m.lower() == model_lower:
            return m   # return exact NHTSA casing
        if re.sub(r'\s+', '', m.lower()) == model_compact:
            return m   # match after whitespace normalization (e.g. "RS3" → "RS 3")
    # Partial match: query is contained in an NHTSA name (forward direction only).
    # Use compacted forms to avoid "s3" matching inside "rs3".
    # We intentionally skip the reverse direction (NHTSA name ⊆ query) because
    # short historical NHTSA names (e.g. "600") would falsely match inside longer
    # user inputs like "gls600".
    candidates = [
        m for m in models
        if model_compact in re.sub(r'\s+', '', m.lower())
    ]
    if len(candidates) == 1:
        return candidates[0]
    return model   # no match — return as-is


def model_exists(make: str, model: str) -> bool:
    """Return True if NHTSA knows this make+model combination."""
    return canonicalize_model(make, model) != model or model in get_models_for_make(make)
