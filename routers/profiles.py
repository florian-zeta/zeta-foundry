import random
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from core.data_loader import load_profiles, enhance_profile, get_vertical

router = APIRouter(tags=["profiles"])


class ICPParams(BaseModel):
    target_states: Optional[list[str]] = None
    target_titles: Optional[list[str]] = None
    min_engagement: Optional[int] = None


class EnhanceRequest(BaseModel):
    vertical: str = Field(
        ...,
        description="Industry vertical. Options: hr_software, retail, financial_services, healthcare",
        example="hr_software"
    )
    icp_description: Optional[str] = Field(
        None,
        description="Plain English ICP description — used for context only, not parsed",
        example="HR Directors at mid-market companies 200-2000 employees"
    )
    icp: Optional[ICPParams] = Field(
        None,
        description="Structured ICP filters for scoring profile match"
    )
    count: int = Field(
        200,
        ge=10,
        le=1064,
        description="How many profiles to return (10-1064)",
        example=200
    )
    seed: Optional[int] = Field(
        None,
        description="Random seed for reproducible results — useful for demos"
    )


class EnhanceResponse(BaseModel):
    vertical: str
    count: int
    profiles: list[dict]
    identity_summary: dict
    sample_titles: list[str]


@router.post(
    "/enhance-profiles",
    response_model=EnhanceResponse,
    summary="Enhance base profiles with vertical attributes",
    description=(
        "Takes the 1,064 base profiles and injects industry-specific attributes: "
        "job titles, firmographics, behavioral signals, lifecycle stage, and engagement score. "
        "Returns a coherent audience that feels like it belongs to one client universe."
    )
)
def enhance_profiles(req: EnhanceRequest):
    all_profiles = load_profiles()
    vertical_config = get_vertical(req.vertical)

    # Reproducible sampling if seed provided
    rng = random.Random(req.seed or 42)
    sampled = rng.sample(all_profiles, min(req.count, len(all_profiles)))

    enhanced = [enhance_profile(p, vertical_config, req.icp) for p in sampled]

    # Identity tier summary
    tiers = {"known": 0, "email-known": 0, "anonymous": 0}
    for p in enhanced:
        tiers[p["identity_tier"]] += 1

    # Sample of job titles for agent to reference
    titles = list({p["job_title"] for p in enhanced})[:8]

    return EnhanceResponse(
        vertical=req.vertical,
        count=len(enhanced),
        profiles=enhanced,
        identity_summary=tiers,
        sample_titles=titles,
    )
