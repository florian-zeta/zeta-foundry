import uuid
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(tags=["campaign"])


class CampaignSchedule(BaseModel):
    launch_type: str = Field(
        "send_later",
        description="send_now, send_later, recurring, api_triggered",
        example="send_later"
    )
    send_at: Optional[str] = Field(
        None,
        description="ISO 8601 datetime for scheduled send",
        example="2026-05-10T18:00:00"
    )
    timezone: str = Field(
        "America/New_York",
        description="ZoneInfo timezone string",
        example="America/New_York"
    )


class BuildCampaignRequest(BaseModel):
    brand_name: str = Field(..., example="Buffalo Wild Wings")
    campaign_name: str = Field(..., example="BWW Loyalty Reactivation — May 2026")
    channel: str = Field(
        "email",
        description="email, sms, push",
        example="email"
    )
    segment_ids: Optional[list[str]] = Field(
        None,
        description="ZMP segment IDs to attach (from segment_creator or build-segments output)",
        example=["seg_abc123", "seg_def456"]
    )
    template_id: Optional[str] = Field(
        None,
        description="ZMP template ID (from Create Snippet or build-html output)",
        example="tpl_xyz789"
    )
    subject_line: str = Field(..., example="Come back. First order of wings is on us.")
    from_name: str = Field(..., example="Buffalo Wild Wings")
    from_email: str = Field(..., example="rewards@buffalowildwings.com")
    schedule: CampaignSchedule = Field(default_factory=CampaignSchedule)
    vertical: str = Field(..., example="retail")


@router.post(
    "/build-campaign",
    summary="Generate a ZMP campaign configuration payload",
    description=(
        "Fallback campaign builder. Produces a ZMP-compatible campaign payload. "
        "Use native ZMP Campaigns_creator capability first — "
        "only call this endpoint if native capability is unavailable or underperforms. "
        "Returns a payload you can POST to the ZMP campaigns API directly."
    )
)
def build_campaign(req: BuildCampaignRequest):
    campaign_id = f"camp_{uuid.uuid4().hex[:8]}"

    payload = {
        "campaign_id": campaign_id,
        "name": req.campaign_name,
        "channel": req.channel,
        "status": "draft",
        "from_name": req.from_name,
        "from_email": req.from_email,
        "subject_line": req.subject_line,
        "segments": req.segment_ids or [],
        "template_id": req.template_id,
        "launch": {
            "type": req.schedule.launch_type,
            "send_at": req.schedule.send_at,
            "timezone": req.schedule.timezone,
        },
        "source": "zeta-sandbox-foundry",
        "vertical": req.vertical,
    }

    instructions = _channel_instructions(req.channel)

    return {
        "campaign_id": campaign_id,
        "campaign_name": req.campaign_name,
        "channel": req.channel,
        "zmp_payload": payload,
        "next_step": instructions,
        "note": (
            "This is a draft payload. "
            "If native Campaigns_creator is available, prefer that — "
            "it will create the campaign directly in ZMP without manual import."
        ),
    }


def _channel_instructions(channel: str) -> str:
    steps = {
        "email": "POST zmp_payload to ZMP /campaigns endpoint, then attach template and launch",
        "sms": "POST zmp_payload to ZMP /campaigns endpoint, confirm SMS provider auto-selection",
        "push": "POST zmp_payload to ZMP /campaigns endpoint, confirm push certificate is active",
    }
    return steps.get(channel, "POST zmp_payload to ZMP /campaigns endpoint")
