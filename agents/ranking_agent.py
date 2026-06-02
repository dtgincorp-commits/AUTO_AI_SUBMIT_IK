from agents.models import CarPreferences, CarListing
from config import MAX_RESULTS


def run_ranking_agent(prefs: CarPreferences, listings: list[CarListing]) -> list[CarListing]:
    from agents.rag_agent import is_rag_available, query_market_data

    market_context = ""
    if is_rag_available():
        docs = query_market_data(prefs.make, prefs.model, prefs.location, n_results=1)
        if docs:
            market_context = docs[0][:300]

    scored = []
    for listing in listings:
        breakdown = {}

        # Model + trim match (50 points) — inferred from listing title
        l_title = (listing.title or "").lower().strip()
        p_model = (prefs.model or "").lower().strip()
        p_trim  = (prefs.trim  or "").lower().strip()
        _trim_has = p_trim and p_trim not in ("any", "")

        if not p_model or p_model == "any":
            model_pts, model_reason = 50.0, "No model preference — full marks"
        elif p_model in l_title:
            if _trim_has and p_trim in l_title:
                model_pts, model_reason = 50.0, f"Model + trim '{prefs.trim}' found in title"
            elif _trim_has:
                model_pts, model_reason = 30.0, f"Model found but trim '{prefs.trim}' not in title"
            else:
                model_pts, model_reason = 50.0, f"Model '{prefs.model}' found in title"
        elif any(w in l_title for w in p_model.split() if len(w) > 2):
            model_pts, model_reason = 25.0, f"Model partially matched in title"
        else:
            model_pts, model_reason = 0.0, f"Model '{prefs.model}' not found in title"
        breakdown["model"] = {"points": model_pts, "max": 50, "reason": model_reason}

        # Price proximity (20 points max)
        mid_price = (prefs.price_min + prefs.price_max) / 2
        price_range = max(prefs.price_max - prefs.price_min, 1)
        price_diff = abs(listing.price - mid_price)
        price_pts = round(max(0, 20 - (price_diff / price_range) * 20), 1)
        breakdown["price"] = {
            "points": price_pts,
            "max": 20,
            "reason": f"${listing.price:,} is ${price_diff:,.0f} from your budget midpoint (${mid_price:,.0f})",
        }

        # Mileage (15 points max)
        # Scraped sources (Craigslist, CarGurus, eBay) return mileage=0 when unknown,
        # not when the car actually has 0 miles. Treat 0 as unknown → half credit.
        _SCRAPED = {"CarGurus", "Craigslist", "eBay Motors"}
        mileage_unknown = listing.mileage == 0 and listing.source in _SCRAPED
        if mileage_unknown:
            mileage_pts = 7.5
            reason = "Mileage not reported by this source — partial credit"
        elif prefs.max_mileage and listing.mileage <= prefs.max_mileage:
            mileage_pts = round(15 * (1 - listing.mileage / prefs.max_mileage), 1)
            reason = f"{listing.mileage:,} mi is {prefs.max_mileage - listing.mileage:,} mi under your {prefs.max_mileage:,} mi cap"
        elif prefs.max_mileage and listing.mileage > prefs.max_mileage:
            mileage_pts = 0.0
            reason = f"{listing.mileage:,} mi exceeds your {prefs.max_mileage:,} mi cap"
        else:
            mileage_pts = 15.0
            reason = "No mileage cap set — full marks"
        breakdown["mileage"] = {"points": mileage_pts, "max": 15, "reason": reason}

        # Exterior color (10 points)
        if not prefs.exterior_color:
            ext_pts, ext_reason = 10.0, "No color preference — full marks"
        elif prefs.exterior_color and listing.exterior_color:
            if prefs.exterior_color.lower() in listing.exterior_color.lower():
                ext_pts, ext_reason = 10.0, f"'{listing.exterior_color}' matches your preference '{prefs.exterior_color}'"
            else:
                ext_pts, ext_reason = 0.0, f"'{listing.exterior_color}' does not match your preference '{prefs.exterior_color}'"
        else:
            ext_pts, ext_reason = 5.0, "Color preference set but listing color unknown"
        breakdown["exterior_color"] = {"points": ext_pts, "max": 10, "reason": ext_reason}

        # Interior color (5 points)
        if not prefs.interior_color:
            int_pts, int_reason = 5.0, "No color preference — full marks"
        elif prefs.interior_color and listing.interior_color:
            if prefs.interior_color.lower() in listing.interior_color.lower():
                int_pts, int_reason = 5.0, f"'{listing.interior_color}' matches your preference '{prefs.interior_color}'"
            else:
                int_pts, int_reason = 0.0, f"'{listing.interior_color}' does not match your preference '{prefs.interior_color}'"
        else:
            int_pts, int_reason = 2.5, "Color preference set but listing color unknown"
        breakdown["interior_color"] = {"points": int_pts, "max": 5, "reason": int_reason}

        total = model_pts + price_pts + mileage_pts + ext_pts + int_pts
        listing.match_score = round(total, 1)
        if market_context:
            breakdown["market_insight"] = {
                "points": 0,
                "max": 0,
                "reason": market_context,
            }
        listing.score_breakdown = breakdown
        scored.append(listing)

    scored.sort(key=lambda x: x.match_score or 0, reverse=True)
    return scored[:MAX_RESULTS]
