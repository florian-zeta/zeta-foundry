import httpx
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(tags=["audience"])


class LoadAudienceRequest(BaseModel):
    profiles: list[dict] = Field(
        ...,
        description="Enhanced profiles from /enhance-profiles"
    )
    site_id: str = Field(
        ...,
        description="ZMP site ID e.g. 'client-services-sandbox'",
        example="client-services-sandbox"
    )
    api_key: str = Field(
        ...,
        description="32-character ZMP REST API key from Settings → Integrations → Keys & Apps",
        example="your-32-char-api-key-here"
    )
    batch_size: int = Field(
        25,
        description="How many records to POST per batch (default 25)",
        ge=1,
        le=50
    )


class LoadAudienceResponse(BaseModel):
    site_id: str
    total: int
    succeeded: int
    failed: int
    errors: list[str]


def _profile_to_subscriber(profile: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    email = None
    phone = None
    for contact in profile.get("contacts", []):
        if contact.get("contact_type") == "email":
            email = contact.get("contact_value")
        elif contact.get("contact_type") == "phone":
            phone = contact.get("contact_value")

    properties = {
        "first_name": profile.get("first_name", ""),
        "last_name": profile.get("last_name", ""),
        "name": f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip(),
        "gender": profile.get("gender", ""),
        "address_1": profile.get("address_1", ""),
        "city": profile.get("city", ""),
        "state": profile.get("state", ""),
        "zip": profile.get("zip", ""),
        "country": profile.get("country", "US"),
        "z_city": profile.get("city", ""),
        "z_state": profile.get("state", ""),
        "z_zip": profile.get("zip", ""),
        "z_country": profile.get("country", "US"),
        "created_at": now,
        "created_source": "zeta-sandbox-foundry",
        "last_updated": now,
        "last_updated_source": "zeta-sandbox-foundry",
        "has_active_email": "true" if email else "false",
        "has_active_phone": "true" if phone else "false",
        "has_active_push_device": "false",
        "has_active_subscription": "true" if profile.get("contacts", [{}])[0].get("subscription_status") == "active" else "false",
        "known_to_customer": True,
        "known_to_zeta": bool(profile.get("zync_id")),
        "job_title": profile.get("job_title", ""),
        "industry": profile.get("industry", ""),
        "company_size": profile.get("company_size", ""),
        "lifecycle_stage": profile.get("lifecycle_stage", ""),
        "engagement_score": str(profile.get("engagement_score", 0)),
        "identity_tier": profile.get("identity_tier", "anonymous"),
        "pain_point_affinity": profile.get("pain_point_affinity", ""),
    }

    properties = {k: v for k, v in properties.items() if v != "" and v is not None}

    subscriber: dict = {
        "subscriber": {
            "user_id": profile.get("user_id", ""),
            "properties": properties
        }
    }

    contacts = []
    if email:
        contacts.append({
            "contact_type": "email",
            "contact_value": email,
            "subscription_status": profile.get("contacts", [{}])[0].get("subscription_status", "active")
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
    profile: dict
) -> tuple[bool, Optional[str]]:
    payload = _profile_to_subscriber(profile)
    try:
        response = await client.post(url, json=payload, auth=auth, timeout=15.0)
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
        "Posts enhanced profiles to ZMP's subscriber API in batches. "
        "Requires a valid ZMP site ID and REST API key. "
        "The API key is used only for this request and is never stored."
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
                _post_single(client, url, auth, profile)
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