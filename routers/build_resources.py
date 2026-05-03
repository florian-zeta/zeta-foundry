import httpx
import asyncio
import random
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(tags=["resources"])

# City coordinates for location resources
CITY_COORDS = [
    {"city": "Nashville", "state": "TN", "lat": 36.0662, "lng": -86.9639, "zip": "37221", "street": "2125 Hillsboro Ave"},
    {"city": "Austin", "state": "TX", "lat": 30.2672, "lng": -97.7431, "zip": "78701", "street": "415 Colorado St"},
    {"city": "Dallas", "state": "TX", "lat": 32.7767, "lng": -96.7970, "zip": "75201", "street": "1201 Elm St"},
    {"city": "Houston", "state": "TX", "lat": 29.7604, "lng": -95.3698, "zip": "77002", "street": "811 Main St"},
    {"city": "Orlando", "state": "FL", "lat": 28.5383, "lng": -81.3792, "zip": "32801", "street": "300 S Orange Ave"},
    {"city": "Miami", "state": "FL", "lat": 25.7617, "lng": -80.1918, "zip": "33101", "street": "1601 Biscayne Blvd"},
    {"city": "Columbus", "state": "OH", "lat": 39.9612, "lng": -82.9988, "zip": "43215", "street": "100 E Broad St"},
    {"city": "Washington", "state": "DC", "lat": 38.9072, "lng": -77.0369, "zip": "20001", "street": "601 F St NW"},
    {"city": "Los Angeles", "state": "CA", "lat": 34.0522, "lng": -118.2437, "zip": "90001", "street": "700 W 7th St"},
]


class ResourceItem(BaseModel):
    resource_id: str = Field(..., example="foundry_product_001")
    resource_type: str = Field(..., example="product")
    title: str = Field(..., example="Mango Habanero Wings")
    description: str = Field(..., example="Our signature heat with a sweet mango finish")
    body: str = Field("", example="Crispy wings tossed in our house-made mango habanero sauce")
    url: str = Field(..., example="https://www.buffalowildwings.com/menu")
    thumbnail: str = Field(..., example="https://placehold.co/400x300?text=Mango+Habanero")
    brand: Optional[str] = Field(None, example="Buffalo Wild Wings")
    category_1: Optional[str] = Field(None, example="Wings")
    category_2: Optional[str] = Field(None, example="Sauced")
    price_min: Optional[float] = Field(None, example=12.99)
    price_max: Optional[float] = Field(None, example=18.99)
    currency: Optional[str] = Field(None, example="USD")
    location_street: Optional[str] = Field(None)
    location_city: Optional[str] = Field(None)
    location_state: Optional[str] = Field(None)
    location_postal_code: Optional[str] = Field(None)
    location_country: Optional[str] = Field(None)
    location_phone: Optional[str] = Field(None)
    location_lat: Optional[float] = Field(None)
    location_lng: Optional[float] = Field(None)


class BuildResourcesRequest(BaseModel):
    site_id: str = Field(..., example="buffalo-wild-wings-crm-demo-2025")
    api_key: str = Field(..., example="your-api-key-here")
    brand_name: str = Field(..., example="Buffalo Wild Wings")
    vertical: str = Field(..., example="retail")
    resource_types: list[str] = Field(
        ...,
        description="List of resource types to generate e.g. ['product', 'location']",
        example=["product", "location"]
    )
    items_per_type: int = Field(
        9,
        ge=1,
        le=20,
        description="Number of resources per type (default 9 — minimum for recommendations engine)"
    )
    product_names: Optional[list[str]] = Field(
        None,
        description="Agent-provided product/service names from brand research"
    )
    location_cities: Optional[list[str]] = Field(
        None,
        description="Agent-provided city names for location resources"
    )


class BuildResourcesResponse(BaseModel):
    site_id: str
    total: int
    succeeded: int
    failed: int
    resource_counts: dict
    errors: list[str]


def _make_resource_payload(item: ResourceItem) -> dict:
    """Build the ZMP resource PUT payload from a ResourceItem."""
    now_ts = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "resource-id": item.resource_id,
        "resource-type": item.resource_type,
        "title": item.title,
        "description": item.description,
        "body": item.body,
        "url": item.url,
        "thumbnail": item.thumbnail,
        "modDate": now_ts,
        "pubDate": now_ts,
    }
    if item.brand:
        payload["brand"] = item.brand
    if item.category_1:
        payload["category_1"] = item.category_1
    if item.category_2:
        payload["category_2"] = item.category_2
    if item.price_min is not None:
        payload["price_min"] = item.price_min
    if item.price_max is not None:
        payload["price_max"] = item.price_max
    if item.currency:
        payload["currency"] = item.currency
    if item.location_street:
        payload["location_street"] = item.location_street
    if item.location_city:
        payload["location_city"] = item.location_city
    if item.location_state:
        payload["location_state"] = item.location_state
    if item.location_postal_code:
        payload["location_postal_code"] = item.location_postal_code
    if item.location_country:
        payload["location_country"] = item.location_country
    if item.location_phone:
        payload["location_phone"] = item.location_phone
    if item.location_lat is not None:
        payload["location_lat"] = item.location_lat
    if item.location_lng is not None:
        payload["location_lng"] = item.location_lng
    return payload


def _generate_products(
    brand_name: str,
    vertical: str,
    count: int,
    product_names: Optional[list[str]],
    run_ts: str
) -> list[ResourceItem]:
    """Generate product resources from agent-provided names or vertical defaults."""
    rng = random.Random(run_ts)

    # Use agent-provided names if available, else fall back to vertical defaults
    if product_names and len(product_names) >= count:
        names = product_names[:count]
    else:
        names = _default_product_names(vertical, brand_name)[:count]

    items = []
    for i, name in enumerate(names):
        idx = str(i + 1).zfill(3)
        encoded = name.replace(" ", "+")
        price = round(rng.uniform(8.99, 49.99), 2)
        items.append(ResourceItem(
            resource_id=f"foundry_product_{idx}_{run_ts}",
            resource_type="product",
            title=name,
            description=f"{name} — available at {brand_name}",
            body=f"Enjoy {name} at your nearest {brand_name} location.",
            url=f"https://www.{brand_name.lower().replace(' ', '')}.com/menu",
            thumbnail=f"https://placehold.co/400x300/333333/ffffff?text={encoded}",
            brand=brand_name,
            category_1=_product_category(vertical),
            price_min=price,
            price_max=round(price * 1.3, 2),
            currency="USD",
        ))
    return items


def _generate_locations(
    brand_name: str,
    count: int,
    location_cities: Optional[list[str]],
    run_ts: str
) -> list[ResourceItem]:
    """Generate location resources."""
    rng = random.Random(run_ts + "loc")
    coords = CITY_COORDS[:count]

    items = []
    for i, geo in enumerate(coords):
        idx = str(i + 1).zfill(3)
        phone = f"+1{rng.randint(200,999)}{rng.randint(200,999)}{rng.randint(1000,9999)}"
        city_name = location_cities[i] if location_cities and i < len(location_cities) else geo["city"]
        encoded = f"{brand_name}+{geo['city']}".replace(" ", "+")
        items.append(ResourceItem(
            resource_id=f"foundry_location_{idx}_{run_ts}",
            resource_type="location",
            title=f"{brand_name} — {geo['city']}, {geo['state']}",
            description=f"Visit {brand_name} in {geo['city']}, {geo['state']}",
            body=f"Your local {brand_name} in {geo['city']}. Open 7 days a week.",
            url=f"https://www.{brand_name.lower().replace(' ', '')}.com/locations",
            thumbnail=f"https://placehold.co/400x300/444444/ffffff?text={encoded}",
            brand=brand_name,
            category_1="Location",
            location_street=geo["street"],
            location_city=geo["city"],
            location_state=geo["state"],
            location_postal_code=geo["zip"],
            location_country="US",
            location_phone=phone,
            location_lat=geo["lat"],
            location_lng=geo["lng"],
        ))
    return items


def _default_product_names(vertical: str, brand_name: str) -> list[str]:
    defaults = {
        "retail": [
            "Classic Wings", "Boneless Wings", "Loaded Nachos",
            "Buffalo Wrap", "Chicken Tenders", "Cheese Curds",
            "Soft Pretzel", "Street Tacos", "Mozzarella Sticks"
        ],
        "financial_services": [
            "Checking Account", "Savings Account", "Credit Card",
            "Home Mortgage", "Auto Loan", "Personal Loan",
            "Investment Account", "Business Checking", "CD Account"
        ],
        "healthcare": [
            "Annual Wellness Visit", "Telehealth Consultation", "Physical Therapy",
            "Mental Health Services", "Urgent Care Visit", "Preventive Screening",
            "Chronic Care Management", "Specialist Referral", "Lab Services"
        ],
        "hr_software": [
            "Core HR Module", "Payroll Processing", "Benefits Administration",
            "Performance Management", "Onboarding Suite", "Learning Management",
            "Analytics Dashboard", "Compliance Tools", "Mobile App Access"
        ],
    }
    return defaults.get(vertical, defaults["retail"])


def _product_category(vertical: str) -> str:
    categories = {
        "retail": "Menu Item",
        "financial_services": "Financial Product",
        "healthcare": "Healthcare Service",
        "hr_software": "Software Module",
    }
    return categories.get(vertical, "Product")


async def _put_resource(
    client: httpx.AsyncClient,
    url: str,
    auth: tuple,
    item: ResourceItem
) -> tuple[bool, Optional[str]]:
    payload = _make_resource_payload(item)
    try:
        response = await client.put(
            url,
            json=payload,
            auth=auth,
            timeout=15.0,
            headers={"Accept": "application/json"}
        )
        if response.status_code in (200, 201):
            return True, None
        else:
            return False, f"{item.resource_id}: HTTP {response.status_code} — {response.text[:100]}"
    except Exception as e:
        return False, f"{item.resource_id}: {str(e)[:100]}"


@router.post(
    "/build-resources",
    response_model=BuildResourcesResponse,
    summary="Generate and load resources into ZMP",
    description=(
        "Generates product and/or location resources and PUTs them to the ZMP resources API. "
        "Pass agent-provided product_names and location_cities from brand research for best results. "
        "Falls back to vertical defaults if not provided. "
        "Minimum 9 items per type recommended for recommendations engine."
    )
)
async def build_resources(req: BuildResourcesRequest):
    run_ts = str(int(datetime.now(timezone.utc).timestamp()))
    auth = ("api", req.api_key)

    all_items: list[ResourceItem] = []

    for rtype in req.resource_types:
        if rtype == "product":
            all_items.extend(_generate_products(
                req.brand_name, req.vertical,
                req.items_per_type, req.product_names, run_ts
            ))
        elif rtype == "location":
            all_items.extend(_generate_locations(
                req.brand_name, req.items_per_type,
                req.location_cities, run_ts
            ))

    if not all_items:
        raise HTTPException(status_code=400, detail="No resource types recognized")

    succeeded = 0
    failed = 0
    errors = []
    resource_counts: dict = {}

    async with httpx.AsyncClient() as client:
        tasks = [
            _put_resource(
                client,
                f"https://api.zetaglobal.net/ver2/{req.site_id}/resources/{item.resource_id}",
                auth,
                item
            )
            for item in all_items
        ]
        results = await asyncio.gather(*tasks)
        for item, (success, error) in zip(all_items, results):
            if success:
                succeeded += 1
                resource_counts[item.resource_type] = resource_counts.get(item.resource_type, 0) + 1
            else:
                failed += 1
                if error:
                    errors.append(error)

    return BuildResourcesResponse(
        site_id=req.site_id,
        total=len(all_items),
        succeeded=succeeded,
        failed=failed,
        resource_counts=resource_counts,
        errors=errors[:10]
    )
