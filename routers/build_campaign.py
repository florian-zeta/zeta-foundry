import httpx
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(tags=["campaign"])
logger = logging.getLogger(__name__)


class BuildCampaignRequest(BaseModel):
    site_id: str = Field(..., example="foundry")
    api_key: str = Field(..., example="your-api-key-here")
    campaign_name: str = Field(..., example="True Religion — Abandoned Cart — 1746321234")
    subject_line: str = Field(..., example="You left something behind")
    preheader_text: Optional[str] = Field(None, example="Your cart is waiting")
    from_email: str = Field("foundry@zetademos.com")
    from_name: str = Field(..., example="True Religion")
    segment_id: Optional[int] = Field(None, description="Numeric segment ID for audience")
    snippet_names: list[str] = Field(
        ...,
        description="Ordered list of snippet names to assemble as campaign body"
    )


class BuildCampaignResponse(BaseModel):
    site_id: str
    campaign_name: str
    campaign_id: Optional[str]
    status: str
    error: Optional[str]


def _assemble_message_html(snippet_names: list[str]) -> str:
    lines = [
        '<!DOCTYPE html>',
        '<html>',
        '<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>',
        '<body style="margin:0;padding:0;">',
    ]
    for name in snippet_names:
        lines.append(f"{{% snippet name: '{name}' %}}")
    lines.extend(['</body>', '</html>'])
    return '\n'.join(lines)


@router.post(
    "/build-campaign",
    response_model=BuildCampaignResponse,
    summary="Create a ZMP broadcast campaign via REST API",
    description=(
        "Creates a draft broadcast campaign and sets the email content "
        "using snippet tags assembled from the provided snippet names. "
        "Two-step: POST /broadcasts to create, PATCH /content to set HTML."
    )
)
async def build_campaign(req: BuildCampaignRequest):
    auth = ("api", req.api_key)
    base_url = f"https://api.zetaglobal.net/ver2/{req.site_id}"
    message_html = _assemble_message_html(req.snippet_names)

    logger.info(f"build_campaign: site={req.site_id} name={req.campaign_name}")

    # Step 1 — Create broadcast campaign shell
    broadcast_payload = {
        "campaign_name": req.campaign_name,
        "status": "draft",
        "timezone": "America/New_York",
        "versions": [
            {
                "name": req.campaign_name,
                "channel": "email",
                "message_templates": [
                    {
                        "index": 0,
                        "subject": req.subject_line,
                        "preheader_text": req.preheader_text or "",
                        "from": req.from_email,
                        "message": message_html,
                    }
                ],
                **({"audience": {"segments": {"include": [req.segment_id]}}} if req.segment_id else {})
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/broadcasts/",
            json=broadcast_payload,
            auth=auth,
            headers={"Accept": "application/json", "Content-Type": "application/json"}
        )

    logger.info(f"build_campaign broadcast response: {response.status_code} {response.text[:200]}")

    if response.status_code in (200, 201):
        data = response.json()
        campaign_id = str(
            data.get("id") or
            data.get("campaign_id") or
            data.get("campaign", {}).get("id") or ""
        )
        return BuildCampaignResponse(
            site_id=req.site_id,
            campaign_name=req.campaign_name,
            campaign_id=campaign_id,
            status="created",
            error=None
        )
    else:
        return BuildCampaignResponse(
            site_id=req.site_id,
            campaign_name=req.campaign_name,
            campaign_id=None,
            status="failed",
            error=f"HTTP {response.status_code} — {response.text[:300]}"
        )