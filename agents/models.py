from pydantic import BaseModel
from typing import Optional


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


class CarListing(BaseModel):
    title: str
    price: int
    mileage: int
    year: int
    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    dealer_name: Optional[str] = None
    location: Optional[str] = None
    listing_url: Optional[str] = None
    match_score: Optional[float] = None
    score_breakdown: Optional[dict] = None
    source: Optional[str] = None
