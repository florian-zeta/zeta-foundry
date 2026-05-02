import httpx
import asyncio
import random
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(tags=["audience"])

BROWSERS = ["Chrome", "Safari", "Firefox", "Edge"]
DEVICES = ["PC", "Mobile", "Tablet"]
OS_OPTIONS = ["Mac OS X", "Windows", "iOS", "Android"]
TIMEZONES = ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"]

STORE_LOCATIONS = [
    {"city": "Nashville", "state": "TN", "name": "BWW Nashville", "lat": 36.0662, "lng": -86.9639, "zip": "37221"},
    {"city": "Austin", "state": "TX", "name": "BWW Austin", "lat": 30.2672, "lng": -97.7431, "zip": "78701"},
    {"city": "Dallas", "state": "TX", "name": "BWW Dallas", "lat": 32.7767, "lng": -96.7970, "zip": "75201"},
    {"city": "Houston", "state": "TX", "name": "BWW Houston", "lat": 29.7604, "lng": -95.3698, "zip": "77002"},
    {"city": "Orlando", "state": "FL", "name": "BWW Orlando", "lat": 28.5383, "lng": -81.3792, "zip": "32801"},
    {"city": "Miami", "state": "FL", "name": "BWW Miami", "lat": 25.7617, "lng": -80.1918, "zip": "33101"},
    {"city": "Columbus", "state": "OH", "name": "BWW Columbus", "lat": 39.9612, "lng": -82.9988, "zip": "43215"},
    {"city": "Washington", "state": "DC", "name": "BWW DC", "lat": 38.9072, "lng": -77.0369, "zip": "20001"},
    {"city": "Los Angeles", "state": "CA", "name": "BWW LA", "lat": 34.0522, "lng": -118.2437, "zip": "90001"},
    {"city": "Chicago", "state": "IL", "name": "BWW Chicago", "lat": 41.8781, "lng": -87.6298, "zip": "60601"},
]

# Vertical-specific branch/location names
BRANCH_NAMES = {
    "financial_services": [
        "Downtown Financial Center", "Westside Branch", "Eastside Branch",
        "North Metro Branch", "South Plaza Branch", "University District Branch",
    ],
    "healthcare": [
        "Main Campus Clinic", "North Health Center", "Westside Medical",
        "Downtown Wellness Center", "East Campus Care", "South District Health",
    ],
    "hr_software": [
        "HQ Office", "West Coast Hub", "East Coast Hub",
        "Central Region Office", "Remote", "Satellite Office",
    ],
}

BWW_SAUCES = [
    "Blazin'", "Mango Habanero", "Honey BBQ", "Medium",
    "Asian Zing", "Parmesan Garlic", "Buffalo", "Hot BBQ",
    "Lemon Pepper", "Desert Heat", "Thai Curry", "Wild"
]

HR_TITLES = [
    "HR Director", "VP of People", "Chief People Officer",
    "HR Manager", "Head of Talent", "People Operations Lead",
    "Director of HR", "Senior HR Business Partner",
]

BANK_PRODUCTS = [
    "checking", "savings", "mortgage", "auto_loan",
    "credit_card", "investment", "personal_loan", "business_checking"
]

HEALTH_CONDITIONS = [
    "annual_wellness", "chronic_care", "preventive", "specialist_referral",
    "urgent_care", "telehealth", "physical_therapy", "mental_health"
]


class LoadAudienceRequest(BaseModel):
    profiles: list[dict] = Field(..., description="Enhanced profiles from /enhance-profiles")
    site_id: str = Field(..., example="client-services-sandbox")
    api_key: str = Field(..., example="your-32-char-api-key-here")
    batch_size: int = Field(25, ge=1, le=50)
    vertical: Optional[str] = Field(None, description="Vertical for rich object generation: retail, financial_services, healthcare, hr_software")
    brand_name: Optional[str] = Field(None, description="Brand name for contextual enrichment")


class LoadAudienceResponse(BaseModel):
    site_id: str
    total: int
    succeeded: int
    failed: int
    errors: list[str]


def _random_date(rng, days_ago_min: int, days_ago_max: int) -> str:
    days = rng.randint(days_ago_min, days_ago_max)
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat()


def _retail_enrichment(profile: dict, rng: random.Random, brand_name: str) -> dict:
    """Blazin' Rewards style loyalty + order history for retail/restaurant brands."""
    points = rng.randint(0, 4800)
    visits = rng.randint(1, 48)
    ytd_spend = round(rng.uniform(12, 380), 2)
    blazin_status = ytd_spend >= 250
    days_since_visit = rng.randint(30, 365)
    sauce = rng.choice(BWW_SAUCES)
    order_type = rng.choice(["dine_in", "takeout", "delivery"])

    loyalty = {
        "program_name": "Blazin' Rewards",
        "member_id": f"BR{profile.get('user_id','').replace('user','').zfill(8)}",
        "points_balance": points,
        "points_expiry_days": rng.randint(30, 365),
        "status_tier": "Blazin' Status" if blazin_status else "Standard",
        "blazin_status": blazin_status,
        "ytd_spend": ytd_spend,
        "total_visits": visits,
        "days_since_last_visit": days_since_visit,
        "lapsed": days_since_visit > 90,
        "favorite_sauce": sauce,
        "preferred_order_type": order_type,
        "app_installed": rng.choice([True, False]),
        "push_opted_in": rng.choice([True, False]),
        "enrolled_date": _random_date(rng, 180, 730),
    }

    last_order = {
        "order_type": order_type,
        "order_total": round(rng.uniform(12, 65), 2),
        "items_count": rng.randint(1, 4),
        "favorite_item": f"{sauce} Wings",
        "days_ago": days_since_visit,
        "channel": order_type,
    }

    return {"blazin_rewards": loyalty, "last_order": last_order}


def _financial_enrichment(profile: dict, rng: random.Random, brand_name: str) -> dict:
    """Account summary and product holdings for financial services brands."""
    products = rng.sample(BANK_PRODUCTS, rng.randint(1, 3))
    tenure_years = rng.randint(1, 15)
    balance = round(rng.uniform(500, 85000), 2)
    credit_score_band = rng.choice(["excellent", "good", "fair", "poor"])
    days_since_login = rng.randint(1, 90)

    account_summary = {
        "customer_since_years": tenure_years,
        "products_held": products,
        "primary_product": products[0],
        "estimated_balance_band": (
            "high" if balance > 25000 else
            "medium" if balance > 5000 else "low"
        ),
        "credit_score_band": credit_score_band,
        "days_since_last_login": days_since_login,
        "digital_active": days_since_login < 30,
        "mobile_app_user": rng.choice([True, False]),
        "paperless": rng.choice([True, False]),
        "at_risk": days_since_login > 60,
        "cross_sell_opportunity": len(products) < 3,
        "preferred_channel": rng.choice(["mobile", "online", "branch", "phone"]),
    }

    branch = rng.choice(BRANCH_NAMES["financial_services"])
    preferred_branch = {
        "name": f"{brand_name} {branch}" if brand_name else branch,
        "city": profile.get("city", ""),
        "state": profile.get("state", ""),
    }

    return {"account_summary": account_summary, "preferred_branch": preferred_branch}


def _healthcare_enrichment(profile: dict, rng: random.Random, brand_name: str) -> dict:
    """Patient engagement and care profile for healthcare brands."""
    care_type = rng.choice(HEALTH_CONDITIONS)
    days_since_visit = rng.randint(14, 400)
    next_appt_days = rng.randint(-30, 90)

    patient_profile = {
        "care_type": care_type,
        "days_since_last_visit": days_since_visit,
        "lapsed": days_since_visit > 180,
        "next_appointment_days": next_appt_days if next_appt_days > 0 else None,
        "appointment_adherence_rate": round(rng.uniform(0.5, 1.0), 2),
        "portal_active": rng.choice([True, False]),
        "telehealth_eligible": rng.choice([True, False]),
        "care_gap_open": rng.choice([True, False]),
        "insurance_type": rng.choice(["commercial", "medicare", "medicaid", "self_pay"]),
        "preferred_contact": rng.choice(["email", "sms", "phone", "portal"]),
        "preferred_location": rng.choice(BRANCH_NAMES["healthcare"]),
    }

    return {"patient_profile": patient_profile}


def _hr_software_enrichment(profile: dict, rng: random.Random, brand_name: str) -> dict:
    """Company profile and buying signals for HR software/B2B brands."""
    company_sizes = ["50-200", "200-500", "500-2000", "2000+"]
    size = rng.choice(company_sizes)
    title = rng.choice(HR_TITLES)
    days_since_demo = rng.randint(7, 180)
    score = rng.randint(20, 95)

    company_profile = {
        "job_title": title,
        "department": "Human Resources",
        "company_size": size,
        "industry_segment": rng.choice(["technology", "healthcare", "retail", "manufacturing", "finance"]),
        "current_system": rng.choice(["Workday", "ADP", "BambooHR", "Namely", "None", "Custom"]),
        "pain_point": rng.choice([
            "employee_retention", "onboarding_automation",
            "compliance_reporting", "performance_management",
            "payroll_integration", "analytics"
        ]),
        "engagement_score": score,
        "lead_stage": (
            "hot" if score > 75 else
            "warm" if score > 50 else "cold"
        ),
        "days_since_last_touchpoint": days_since_demo,
        "demo_requested": score > 65,
        "content_downloads": rng.randint(0, 5),
        "webinar_attended": rng.choice([True, False]),
        "decision_maker": title in ["VP of People", "Chief People Officer", "HR Director"],
    }

    return {"company_profile": company_profile}


def _profile_to_subscriber(
    profile: dict,
    vertical: Optional[str] = None,
    brand_name: Optional[str] = None
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    rng = random.Random(profile.get("user_id", "seed"))

    # Extract contacts
    email = None
    phone = None
    sub_status = "active"
    for contact in profile.get("contacts", []):
        if contact.get("contact_type") == "email":
            email = contact.get("contact_value")
            sub_status = contact.get("subscription_status", "active")
        elif contact.get("contact_type") == "phone":
            phone = contact.get("contact_value")

    # Pick nearest store location
    state = profile.get("state", "TX")
    matching = [l for l in STORE_LOCATIONS if l["state"] == state]
    store = rng.choice(matching if matching else STORE_LOCATIONS)

    # Device/session signals
    browser = rng.choice(BROWSERS)
    device = rng.choice(DEVICES)
    os = rng.choice(OS_OPTIONS)
    tz = rng.choice(TIMEZONES)

    # Dates
    signed_up = _random_date(rng, 180, 730)
    last_seen = _random_date(rng, 7, 90)
    last_contact = _random_date(rng, 14, 60)
    last_opened = _random_date(rng, 14, 90)

    properties = {
        # Core identity
        "first_name": profile.get("first_name", ""),
        "last_name": profile.get("last_name", ""),
        "name": f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip(),
        "gender": profile.get("gender", ""),

        # Address
        "address_1": profile.get("address_1", ""),
        "city": profile.get("city", ""),
        "state": profile.get("state", ""),
        "zip": profile.get("zip", ""),
        "country": profile.get("country", "US"),
        "latitude": store["lat"],
        "longitude": store["lng"],

        # Zeta geo fields
        "z_city": profile.get("city", ""),
        "z_state": profile.get("state", ""),
        "z_zip": profile.get("zip", ""),
        "z_country": profile.get("country", "US"),
        "z_latitude": store["lat"],
        "z_longitude": store["lng"],

        # Session signals
        "ns_browser": browser,
        "ns_browser_version": f"{rng.randint(100, 146)}.0.0",
        "ns_city": store["city"],
        "ns_continent": "NA",
        "ns_country": "US",
        "ns_device_type": device,
        "ns_latitude": store["lat"],
        "ns_longitude": store["lng"],
        "ns_metro_code": rng.randint(500, 600),
        "ns_operating_system": os,
        "ns_postal_code": store["zip"],
        "ns_region": store["state"],
        "ns_timezone": tz,

        # Subscription flags
        "has_active_email": "true" if email else "false",
        "has_active_phone": "true" if phone else "false",
        "has_active_push_device": rng.choice(["true", "false"]),
        "has_active_subscription": "true" if sub_status == "active" else "false",

        # Identity
        "known_to_customer": True,
        "known_to_zeta": bool(profile.get("zync_id")),

        # Dates
        "signed_up_at": signed_up,
        "created_at": signed_up,
        "created_source": "zeta-sandbox-foundry",
        "last_updated": now,
        "last_updated_source": "zeta-sandbox-foundry",
        "last_seen": last_seen,
        "last_contact": last_contact,
        "last_opened": last_opened,

        # Foundry base enrichment
        "lifecycle_stage": profile.get("lifecycle_stage", ""),
        "engagement_score": str(profile.get("engagement_score", 0)),
        "identity_tier": profile.get("identity_tier", "anonymous"),
    }

    # Vertical-specific rich objects
    v = (vertical or "").lower()
    enrichment_rng = random.Random(profile.get("user_id", "seed") + "enrichment")

    if v == "retail":
        properties.update(_retail_enrichment(profile, enrichment_rng, brand_name or ""))
    elif v == "financial_services":
        properties.update(_financial_enrichment(profile, enrichment_rng, brand_name or ""))
    elif v == "healthcare":
        properties.update(_healthcare_enrichment(profile, enrichment_rng, brand_name or ""))
    elif v == "hr_software":
        properties.update(_hr_software_enrichment(profile, enrichment_rng, brand_name or ""))

    # Remove empty strings and None
    properties = {k: v for k, v in properties.items() if v != "" and v is not None}

    subscriber: dict = {
        "subscriber": {
            "user_id": profile.get("user_id", ""),
            "properties": properties
        }
    }

    # Contacts
    contacts = []
    if email:
        contacts.append({
            "contact_type": "email",
            "contact_value": email,
            "subscription_status": sub_status
        })
    if phone:
        contacts.append({
            "contact_type": "phone",
            "contact_value": phone
        })
    if contacts:
        subscriber["subscriber"]["contacts"] = contacts

    if profile.get("zync_id"):
        subscriber["subscriber"]["zync_id"] = profile["zync_id"]

    return subscriber


async def _post_single(
    client: httpx.AsyncClient,
    url: str,
    auth: tuple,
    profile: dict,
    vertical: Optional[str],
    brand_name: Optional[str]
) -> tuple[bool, Optional[str]]:
    payload = _profile_to_subscriber(profile, vertical, brand_name)
    try:
        response = await client.post(
            url, json=payload, auth=auth, timeout=15.0,
            headers={"Accept": "application/json"}
        )
        if response.status_code in (200, 201):
            return True, None
        else:
            return False, f"user_id={profile.get('user_id')}: HTTP {response.status_code} — {response.text[:100]}"
    except Exception as e:
        return False, f"user_id={profile.get('user_id')}: {str(e)[:100]}"


@router.post(
    "/load-audience",
    response_model=LoadAudienceResponse,
    summary="Load enhanced profiles directly into ZMP via REST API",
    description=(
        "Posts enhanced profiles to ZMP subscriber API in batches. "
        "Generates vertical-specific rich objects: loyalty program data for retail, "
        "account summaries for financial services, patient profiles for healthcare, "
        "company profiles for HR software. API key is never stored."
    )
)
async def load_audience(req: LoadAudienceRequest):
    if not req.profiles:
        raise HTTPException(status_code=400, detail="No profiles provided")

    url = f"https://api.zetaglobal.net/ver2/{req.site_id}/subscribers"
    auth = ("api", req.api_key)

    succeeded = 0
    failed = 0
    errors = []

    async with httpx.AsyncClient() as client:
        for i in range(0, len(req.profiles), req.batch_size):
            batch = req.profiles[i:i + req.batch_size]
            tasks = [
                _post_single(client, url, auth, profile, req.vertical, req.brand_name)
                for profile in batch
            ]
            results = await asyncio.gather(*tasks)
            for success, error in results:
                if success:
                    succeeded += 1
                else:
                    failed += 1
                    if error:
                        errors.append(error)
            if i + req.batch_size < len(req.profiles):
                await asyncio.sleep(0.5)

    return LoadAudienceResponse(
        site_id=req.site_id,
        total=len(req.profiles),
        succeeded=succeeded,
        failed=failed,
        errors=errors[:10]
    )