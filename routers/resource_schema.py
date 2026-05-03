import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["schema"])

CUSTOMERS_API_TOKEN = os.environ.get("CUSTOMERS_API_TOKEN", "")

RESOURCE_SCHEMA = {
    "data_format": "JSON",
    "data_loader": "SFTP",
    "fields": [
        {"default_value": "", "name": "resource-id", "selector": "resource-id", "selectors": {"JSON": ["resource-id"]}, "type": "TEXT"},
        {"default_value": "", "name": "resource-type", "selector": "resource-type", "selectors": {"JSON": ["resource-type"]}, "type": "TAGSET"},
        {"default_value": "", "name": "title", "selector": "title", "selectors": {"JSON": ["title"]}, "type": "TEXT"},
        {"default_value": "", "name": "role", "selector": "role", "selectors": {"JSON": ["role"]}, "type": "TEXT"},
        {"default_value": "", "name": "first_name", "selector": "first_name", "selectors": {"JSON": ["first_name"]}, "type": "TEXT"},
        {"default_value": "", "name": "last_name", "selector": "last_name", "selectors": {"JSON": ["last_name"]}, "type": "TEXT"},
        {"default_value": "", "name": "email", "selector": "email", "selectors": {"JSON": ["email"]}, "type": "TEXT"},
        {"default_value": "", "name": "phone", "selector": "phone", "selectors": {"JSON": ["phone"]}, "type": "TEXT"},
        {"default_value": "", "name": "description", "selector": "description", "selectors": {"JSON": ["description"]}, "type": "TEXT"},
        {"default_value": "", "name": "url", "selector": "url", "selectors": {"JSON": ["url"]}, "type": "TEXT"},
        {"default_value": "", "name": "thumbnail", "selector": "thumbnail", "selectors": {"JSON": ["thumbnail"]}, "type": "TEXT"},
        {"default_value": "", "name": "body", "selector": "body", "selectors": {"JSON": ["body"]}, "type": "TEXT"},
        {"default_value": "", "name": "brand", "selector": "brand", "selectors": {"JSON": ["brand"]}, "type": "TEXT"},
        {"default_value": "", "name": "category_1", "selector": "category_1", "selectors": {"JSON": ["category_1"]}, "type": "TEXT"},
        {"default_value": "", "name": "category_2", "selector": "category_2", "selectors": {"JSON": ["category_2"]}, "type": "TEXT"},
        {"default_value": "", "name": "category", "selector": "category", "selectors": {"JSON": ["category"]}, "type": "TAGSET"},
        {"default_value": "", "name": "uom", "selector": "uom", "selectors": {"JSON": ["uom"]}, "type": "TEXT"},
        {"default_value": "", "name": "fulfillment", "selector": "fulfillment", "selectors": {"JSON": ["fulfillment"]}, "type": "TAGSET"},
        {"default_value": "", "name": "ships_from_supplier", "selector": "ships_from_supplier", "selectors": {"JSON": ["ships_from_supplier"]}, "type": "FLAG"},
        {"amt_type": "USD", "default_value": "", "name": "price_min", "selector": "price_min", "selectors": {"JSON": ["price_min"]}, "type": "AMOUNT"},
        {"amt_type": "USD", "default_value": "", "name": "price_max", "selector": "price_max", "selectors": {"JSON": ["price_max"]}, "type": "AMOUNT"},
        {"default_value": "", "name": "currency", "selector": "currency", "selectors": {"JSON": ["currency"]}, "type": "TEXT"},
        {"default_value": "", "name": "sale_primary", "selector": "sale_primary", "selectors": {"JSON": ["sale_primary"]}, "type": "TEXT"},
        {"default_value": "", "name": "sale_tags", "selector": "sale_tags", "selectors": {"JSON": ["sale_tags"]}, "type": "TAGSET"},
        {"default_value": "", "name": "sale_discount_text", "selector": "sale_discount_text", "selectors": {"JSON": ["sale_discount_text"]}, "type": "TEXT"},
        {"amt_type": "SECONDS", "default_value": "", "name": "sale_start", "selector": "sale_start", "selectors": {"JSON": ["sale_start"]}, "type": "AMOUNT"},
        {"amt_type": "SECONDS", "default_value": "", "name": "sale_end", "selector": "sale_end", "selectors": {"JSON": ["sale_end"]}, "type": "AMOUNT"},
        {"default_value": "", "name": "language", "selector": "language", "selectors": {"JSON": ["language"]}, "type": "TAGSET"},
        {"amt_type": "SECONDS", "default_value": "", "name": "pubDate", "selector": "pubDate", "selectors": {"JSON": ["pubDate"]}, "type": "AMOUNT"},
        {"amt_type": "SECONDS", "default_value": "", "name": "modDate", "selector": "modDate", "selectors": {"JSON": ["modDate"]}, "type": "AMOUNT"},
        {"default_value": "", "name": "location_street", "selector": "location_street", "selectors": {"JSON": ["location_street"]}, "type": "TEXT"},
        {"default_value": "", "name": "location_city", "selector": "location_city", "selectors": {"JSON": ["location_city"]}, "type": "TEXT"},
        {"default_value": "", "name": "location_state", "selector": "location_state", "selectors": {"JSON": ["location_state"]}, "type": "TEXT"},
        {"default_value": "", "name": "location_postal_code", "selector": "location_postal_code", "selectors": {"JSON": ["location_postal_code"]}, "type": "TEXT"},
        {"default_value": "", "name": "location_country", "selector": "location_country", "selectors": {"JSON": ["location_country"]}, "type": "TEXT"},
        {"default_value": "", "name": "location_phone", "selector": "location_phone", "selectors": {"JSON": ["location_phone"]}, "type": "TEXT"},
        {"default_value": "", "name": "location_hours", "selector": "location_hours", "selectors": {"JSON": ["location_hours"]}, "type": "TAGSET"},
        {"default_value": "", "name": "location_closed", "selector": "location_closed", "selectors": {"JSON": ["location_closed"]}, "type": "FLAG"},
        {"amt_type": "SCORE", "default_value": "", "name": "location_lat", "selector": "location_lat", "selectors": {"JSON": ["location_lat"]}, "type": "AMOUNT"},
        {"amt_type": "SCORE", "default_value": "", "name": "location_lng", "selector": "location_lng", "selectors": {"JSON": ["location_lng"]}, "type": "AMOUNT"},
    ],
    "named_filters": {
        "GLOBAL": {
            "and": [{"existence": {"exists": True, "field": "resource-id"}}]
        },
        "Zeta_All_Resources": {
            "and": [{"existence": {"exists": True, "field": "resource-id"}}]
        },
        "Zeta_All_Locations": {
            "and": [{"overlap": {"field": "resource-type", "match_type": "EXACT", "min": 1, "values": ["location"]}}]
        },
        "All_Products": {
            "and": [{"overlap": {"field": "resource-type", "match_type": "EXACT", "min": 1, "values": ["product"]}}]
        },
        "All_Content": {
            "and": [{"overlap": {"field": "resource-type", "match_type": "EXACT", "min": 1, "values": ["content"]}}]
        }
    },
    "recency_field": "modDate",
    "ingest_from_replicated_event": False,
    "ingestion_required": False,
    "scrape_custom_javascript": False,
    "scrape_rate": 0,
    "skip_resource_validation": False
}


class SetupSchemaRequest(BaseModel):
    site_id: str = Field(..., example="florian-w-sandbox1")


@router.post(
    "/setup-resource-schema",
    summary="Create or update the resource catalog schema for a ZMP site",
    description=(
        "Idempotent — safe to call on every build. "
        "Pushes the standard Foundry resource schema to the ZMP customers API. "
        "Bearer token is stored securely on the server."
    )
)
async def setup_resource_schema(req: SetupSchemaRequest):
    if not CUSTOMERS_API_TOKEN:
        raise HTTPException(status_code=503, detail="CUSTOMERS_API_TOKEN not configured")

    url = f"https://customers.api.zetaglobal.net/site/{req.site_id}/candidates"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(
            url,
            json=RESOURCE_SCHEMA,
            headers={
                "Authorization": CUSTOMERS_API_TOKEN,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    if response.status_code in (200, 201):
        return {
            "site_id": req.site_id,
            "status": "ready",
            "message": "Resource schema configured successfully",
            "fields_count": len(RESOURCE_SCHEMA["fields"])
        }
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Schema setup failed: {response.text[:200]}"
        )
