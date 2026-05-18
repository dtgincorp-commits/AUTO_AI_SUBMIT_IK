from pydantic import BaseModel
from typing import Optional, Dict


class CarPreferences(BaseModel):
    make: str
    model: str
    trim: Optional[str] = None
    price_min: int
    price_max: int
    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    max_mileage: Optional[int] = None
    location: str
    radius_miles: int
    delivery_email: bool = True
    delivery_sms: bool = False
    user_email: Optional[str] = None
    user_phone: Optional[str] = None
    certified_only: bool = False
    condition: Optional[str] = None
    dealer_outreach: bool = False
    broker_name: Optional[str] = None
    broker_email: Optional[str] = None
    broker_phone: Optional[str] = None


class CarListing(BaseModel):
    title: str
    price: int
    mileage: int
    year: int
    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    asking_price: Optional[int] = None  # raw dealer price (0 = not published)
    msrp: Optional[int] = None
    dealer_name: Optional[str] = None
    dealer_phone: Optional[str] = None
    dealer_email: Optional[str] = None
    location: Optional[str] = None
    listing_url: Optional[str] = None
    match_score: Optional[float] = None
    score_breakdown: Optional[dict] = None
    source: Optional[str] = None


class DimensionResult(BaseModel):
    name: str
    passed: bool
    score: float        # 0–25 per dimension
    reason: str
    flag: str           # "pass" | "amber" | "fail"


class CriticResult(BaseModel):
    overall_score: float                      # 0–100, sum of 4 dimensions
    badge: str                                # "green" | "amber" | "red"
    dimensions: Dict[str, DimensionResult]
    revision_needed: bool
    revision_feedback: str
