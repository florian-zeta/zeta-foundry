import httpx
import asyncio
import random
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(tags=["events"])
logger = logging.getLogger(__name__)


class CatalogItem(BaseModel):
    name: str = Field(..., example="Mango Habanero Wings")
    image: str = Field(..., example="https://placehold.co/400x300?text=Mango+Habanero+Wings")
    url: str = Field(..., example="https://www.buffalowildwings.com/menu")
    price: Optional[float] = Field(None, example=14.99)


class BuildEventsRequest(BaseModel):
    site_id: str = Field(..., example="buffalo-wild-wings-crm-demo-2025")
    api_key: str = Field(..., example="your-api-key-here")
    uids: list[str] = Field(..., description="Subscriber UIDs from /load-audience")
    brand_name: str = Field(..., example="Buffalo Wild Wings")
    brand_url: str = Field(..., example="https://www.buffalowildwings.com")
    light_event_names: list[str] = Field(
        ...,
        description="2-3 light behavioral event names appropriate for this brand",
        example=["page_view", "view_menu", "loyalty_checkin"]
    )
    rich_event_name: str = Field(
        ...,
        description="Name of the single rich loopable event per user",
        example="updated_cart"
    )
    rich_items_key: str = Field(
        ...,
        description="Key name for the items array in the rich event properties",
        example="items"
    )
    catalog: list[CatalogItem] = Field(
        ...,
        description="Product/service catalog from brand research"
    )
    events_per_user: int = Field(2, ge=1, le=5)


class BuildEventsResponse(BaseModel):
    site_id: str
    total: int
    succeeded: int
    failed: int
    event_counts: dict
    rich_event_name: str
    rich_items_key: str
    errors: list[str]


def _random_past_date(rng: random.Random, days_ago_min: int, days_ago_max: int) -> str:
    days = rng.randint(days_ago_min, days_ago_max)
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_light_activity(
    uid: str,
    event: str,
    brand_name: str,
    brand_url: str,
    rng: random.Random,
    timestamp: str
) -> dict:
    return {
        "activity": {
            "subscriber": {"uid": uid},
            "event": event,
            "timestamp": timestamp,
            "properties": {
                "source": "zeta-sandbox-foundry",
                "brand": brand_name,
                "url": brand_url,
            }
        }
    }


def _build_rich_activity(
    uid: str,
    rich_event_name: str,
    rich_items_key: str,
    brand_name: str,
    brand_url: str,
    catalog: list[dict],
    rng: random.Random,
    timestamp: str
) -> dict:
    n_items = rng.randint(2, min(3, len(catalog)))
    selected = rng.sample(catalog, n_items)

    items = [
        {
            "name": item["name"],
            "quantity": rng.randint(1, 2),
            "price": item.get("price") or 0,
            "image": item["image"],
            "url": item["url"],
        }
        for item in selected
    ]

    cart_value = round(sum(i["price"] * i["quantity"] for i in items), 2)

    properties = {
        "source": "zeta-sandbox-foundry",
        "brand": brand_name,
        "brand_url": brand_url,
        "cart_id": f"CART-{uid[-8:]}-{rng.randint(1000, 9999)}",
        "cart_value": cart_value,
        "currency": "USD",
        rich_items_key: items,
    }

    return {
        "activity": {
            "subscriber": {"uid": uid},
            "event": rich_event_name,
            "timestamp": timestamp,
            "properties": properties
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
        if response.status_code in (200, 201, 202):
            return True, event_name, None
        else:
            return False, event_name, f"HTTP {response.status_code} — {response.text[:200]}"
    except Exception as e:
        return False, event_name, str(e)[:200]


@router.post(
    "/build-events",
    response_model=BuildEventsResponse,
    summary="Generate light behavioral events plus one rich loopable event per subscriber",
    description=(
        "Creates light behavioral events and one rich self-contained event per subscriber. "
        "Rich event contains full item details for ZML template loops. "
        "No resource_id references — everything needed for HTML rendering is on the event."
    )
)
async def build_events(req: BuildEventsRequest):
    if not req.uids:
        raise HTTPException(status_code=400, detail="No UIDs provided")
    if not req.catalog:
        raise HTTPException(status_code=400, detail="No catalog provided")

    logger.info(
        f"build_events: site={req.site_id} uids={len(req.uids)} "
        f"catalog={len(req.catalog)} rich_event={req.rich_event_name}"
    )

    url = f"https://api.zetaglobal.net/ver2/{req.site_id}/activities"
    auth = ("api", req.api_key)
    catalog = [item.model_dump() for item in req.catalog]

    payloads = []
    for uid in req.uids:
        rng = random.Random(uid)

        for i in range(req.events_per_user):
            event = rng.choice(req.light_event_names)
            ts = _random_past_date(rng, i * 7 + 14, i * 7 + 30)
            payloads.append(_build_light_activity(
                uid, event, req.brand_name, req.brand_url, rng, ts
            ))

        rich_ts = _random_past_date(rng, 1, 7)
        payloads.append(_build_rich_activity(
            uid, req.rich_event_name, req.rich_items_key,
            req.brand_name, req.brand_url, catalog, rng, rich_ts
        ))

    logger.info(f"build_events: {len(payloads)} total payloads to send")

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

    logger.info(f"build_events: succeeded={succeeded} failed={failed}")

    return BuildEventsResponse(
        site_id=req.site_id,
        total=len(payloads),
        succeeded=succeeded,
        failed=failed,
        event_counts=event_counts,
        rich_event_name=req.rich_event_name,
        rich_items_key=req.rich_items_key,
        errors=errors[:10]
    )