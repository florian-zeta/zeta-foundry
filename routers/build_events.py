import httpx
import asyncio
import random
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(tags=["events"])

VERTICAL_EVENTS = {
    "retail": [
        {"event": "page_view", "weight": 3},
        {"event": "view_menu", "weight": 3},
        {"event": "add_to_cart", "weight": 2},
        {"event": "place_order", "weight": 1},
        {"event": "loyalty_checkin", "weight": 2},
    ],
    "financial_services": [
        {"event": "page_view", "weight": 3},
        {"event": "product_view", "weight": 3},
        {"event": "calculator_used", "weight": 2},
        {"event": "application_started", "weight": 1},
        {"event": "login", "weight": 3},
    ],
    "healthcare": [
        {"event": "page_view", "weight": 3},
        {"event": "appointment_viewed", "weight": 3},
        {"event": "appointment_booked", "weight": 1},
        {"event": "portal_login", "weight": 2},
        {"event": "survey_completed", "weight": 1},
    ],
    "hr_software": [
        {"event": "page_view", "weight": 3},
        {"event": "demo_requested", "weight": 1},
        {"event": "whitepaper_downloaded", "weight": 2},
        {"event": "pricing_viewed", "weight": 2},
        {"event": "webinar_attended", "weight": 1},
    ],
}


class BuildEventsRequest(BaseModel):
    site_id: str = Field(..., example="buffalo-wild-wings-crm-demo-2025")
    api_key: str = Field(..., example="your-api-key-here")
    uids: list[str] = Field(
        ...,
        description="Subscriber UIDs returned from /load-audience"
    )
    vertical: str = Field(..., example="retail")
    brand_name: str = Field(..., example="Buffalo Wild Wings")
    resource_ids: Optional[list[str]] = Field(
        None,
        description="Resource IDs from /build-resources to reference in events"
    )
    events_per_user: int = Field(
        3,
        ge=1,
        le=10,
        description="Number of events per subscriber"
    )


class BuildEventsResponse(BaseModel):
    site_id: str
    total: int
    succeeded: int
    failed: int
    event_counts: dict
    errors: list[str]


def _random_past_date(rng: random.Random, days_ago_min: int, days_ago_max: int) -> str:
    days = rng.randint(days_ago_min, days_ago_max)
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick_events(vertical: str, count: int, rng: random.Random) -> list[str]:
    event_pool = VERTICAL_EVENTS.get(vertical, VERTICAL_EVENTS["retail"])
    weighted = []
    for e in event_pool:
        weighted.extend([e["event"]] * e["weight"])
    return [rng.choice(weighted) for _ in range(count)]


def _build_properties(
    event: str,
    vertical: str,
    brand_name: str,
    uid: str,
    resource_ids: Optional[list[str]],
    rng: random.Random,
    timestamp: str
) -> dict:
    base = {
        "source": "zeta-sandbox-foundry",
        "event_timestamp": timestamp,
        "brand": brand_name,
    }

    rid = rng.choice(resource_ids) if resource_ids else f"foundry_product_001"

    if vertical == "retail":
        if event == "place_order":
            return {**base,
                "order_id": f"ORD-{uid[-8:]}-{rng.randint(1000,9999)}",
                "order_total": round(rng.uniform(12, 65), 2),
                "currency": "USD",
                "items": [{"resource_id": rid, "quantity": rng.randint(1, 3)}],
                "service_method": rng.choice(["dine_in", "takeout", "delivery"]),
            }
        elif event == "add_to_cart":
            return {**base,
                "cart_id": f"CART-{uid[-8:]}",
                "cart_value": round(rng.uniform(10, 50), 2),
                "currency": "USD",
                "items": [{"resource_id": rid, "quantity": 1}],
            }
        elif event == "loyalty_checkin":
            return {**base,
                "points_earned": rng.randint(10, 100),
                "visit_type": rng.choice(["dine_in", "takeout"]),
            }
        else:
            return {**base, "resource_id": rid, "page": "menu"}

    elif vertical == "financial_services":
        if event == "application_started":
            return {**base,
                "product_id": rid,
                "application_id": f"APP-{rng.randint(100000, 999999)}",
                "product_type": rng.choice(["checking", "savings", "credit_card"]),
            }
        elif event == "calculator_used":
            return {**base,
                "calculator_type": rng.choice(["mortgage", "savings", "loan"]),
                "estimated_amount": round(rng.uniform(5000, 500000), 2),
            }
        else:
            return {**base, "resource_id": rid, "page": "products"}

    elif vertical == "healthcare":
        if event == "appointment_booked":
            return {**base,
                "appointment_id": f"APT-{rng.randint(10000, 99999)}",
                "care_type": rng.choice(["annual_wellness", "specialist", "urgent_care"]),
                "preferred_date": _random_past_date(rng, 0, 30),
            }
        else:
            return {**base, "resource_id": rid, "page": "services"}

    elif vertical == "hr_software":
        if event == "demo_requested":
            return {**base,
                "demo_id": f"DEMO-{rng.randint(1000, 9999)}",
                "company_size": rng.choice(["50-200", "200-500", "500-2000"]),
                "modules_interested": rng.sample(["payroll", "onboarding", "performance"], 2),
            }
        elif event == "whitepaper_downloaded":
            return {**base,
                "document": rng.choice(["ROI Guide", "Implementation Checklist", "Feature Overview"]),
            }
        else:
            return {**base, "resource_id": rid, "page": "features"}

    return base


def _build_activity(
    uid: str,
    event: str,
    properties: dict,
    timestamp: str
) -> dict:
    return {
        "activity": {
            "subscriber": {"uid": uid},
            "event": event,
            "properties": {
                **properties,
                "event_timestamp": timestamp,
            }
        }
    }


async def _post_event(
    client: httpx.AsyncClient,
    url: str,
    auth: tuple,
    payload: dict
) -> tuple[bool, str, Optional[str]]:
    event_name = payload["activity"]["event"]
    try:
        response = await client.post(
            url, json=payload, auth=auth, timeout=15.0,
            headers={"Accept": "application/json"}
        )
        if response.status_code in (200, 201):
            return True, event_name, None
        else:
            return False, event_name, f"HTTP {response.status_code} — {response.text[:100]}"
    except Exception as e:
        return False, event_name, str(e)[:100]


@router.post(
    "/build-events",
    response_model=BuildEventsResponse,
    summary="Generate and post behavioral events for loaded subscribers",
    description=(
        "Creates realistic behavioral events per subscriber based on vertical. "
        "UIDs must match subscriber UIDs returned from /load-audience. "
        "Pass resource_ids from /build-resources to reference in event properties."
    )
)
async def build_events(req: BuildEventsRequest):
    if not req.uids:
        raise HTTPException(status_code=400, detail="No UIDs provided")

    url = f"https://api.zetaglobal.net/ver2/{req.site_id}/activities"
    auth = ("api", req.api_key)

    payloads = []
    for uid in req.uids:
        rng = random.Random(uid)
        events = _pick_events(req.vertical, req.events_per_user, rng)
        for i, event in enumerate(events):
            ts = _random_past_date(rng, i * 5, i * 5 + 30)
            props = _build_properties(
                event, req.vertical, req.brand_name,
                uid, req.resource_ids, rng, ts
            )
            payloads.append(_build_activity(uid, event, props, ts))

    succeeded = 0
    failed = 0
    errors = []
    event_counts: dict = {}

    async with httpx.AsyncClient() as client:
        tasks = [_post_event(client, url, auth, p) for p in payloads]
        results = await asyncio.gather(*tasks)
        for success, event_name, error in results:
            if success:
                succeeded += 1
                event_counts[event_name] = event_counts.get(event_name, 0) + 1
            else:
                failed += 1
                if error:
                    errors.append(error)

    return BuildEventsResponse(
        site_id=req.site_id,
        total=len(payloads),
        succeeded=succeeded,
        failed=failed,
        event_counts=event_counts,
        errors=errors[:10]
    )
