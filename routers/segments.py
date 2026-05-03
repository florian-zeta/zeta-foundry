from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
import uuid

router = APIRouter(tags=["segments"])


class SegmentRule(BaseModel):
    field: str = Field(..., example="lifecycle_stage")
    operator: str = Field(..., example="equals")
    value: str = Field(..., example="evaluation")


class SegmentDefinition(BaseModel):
    name: str = Field(..., example="High-Intent HR Directors")
    description: Optional[str] = Field(None, example="Mid-funnel prospects showing evaluation signals")
    rules: list[SegmentRule]
    logic: str = Field("AND", description="AND or OR logic across rules")


class BuildSegmentsRequest(BaseModel):
    vertical: str = Field(..., example="hr_software")
    campaign_theme: str = Field(
        ...,
        description="What this campaign is trying to do",
        example="Q4 pipeline push for HR software"
    )
    segments: Optional[list[SegmentDefinition]] = Field(
        None,
        description="Explicit segment definitions. If omitted, foundry generates sensible defaults for the vertical."
    )


class BuiltSegment(BaseModel):
    segment_id: str
    name: str
    description: str
    zmp_payload: dict


@router.post(
    "/build-segments",
    summary="Build ZMP-compatible segment definitions",
    description=(
        "Generates segment JSON ready to import into ZMP. "
        "Pass explicit segment definitions or let the foundry generate sensible defaults "
        "for the vertical and campaign theme."
    )
)
def build_segments(req: BuildSegmentsRequest):
    # If no segments passed, generate smart defaults for the vertical
    definitions = req.segments or _default_segments(req.vertical, req.campaign_theme)

    built = []
    for seg in definitions:
        seg_id = f"seg_{uuid.uuid4().hex[:8]}"
        built.append(
            BuiltSegment(
                segment_id=seg_id,
                name=seg.name,
                description=seg.description or f"Auto-generated for {req.campaign_theme}",
                zmp_payload=_to_zmp_payload(seg_id, seg, req.vertical),
            )
        )

    return {
        "vertical": req.vertical,
        "campaign_theme": req.campaign_theme,
        "segments": [s.model_dump() for s in built],
        "count": len(built),
        "note": "Import each zmp_payload via ZMP Audience API or paste into segment builder",
    }


def _default_segments(vertical: str, campaign_theme: str) -> list[SegmentDefinition]:
    """Generate three sensible default segments for any vertical."""
    defaults = {
        "hr_software": [
            SegmentDefinition(
                name="High-Intent Evaluators",
                description="In evaluation stage with strong engagement",
                rules=[
                    SegmentRule(field="lifecycle_stage", operator="equals", value="evaluation"),
                    SegmentRule(field="engagement_score", operator="greater_than", value="60"),
                ],
                logic="AND"
            ),
            SegmentDefinition(
                name="Warm Prospects",
                description="Consideration stage, any engagement level",
                rules=[
                    SegmentRule(field="lifecycle_stage", operator="equals", value="consideration"),
                ],
                logic="AND"
            ),
            SegmentDefinition(
                name="Known Contacts — Decision Makers",
                description="Fully identity-resolved HR Directors only",
                rules=[
                    SegmentRule(field="identity_tier", operator="equals", value="known"),
                    SegmentRule(field="job_title", operator="contains", value="Director"),
                ],
                logic="AND"
            ),
        ],
        "retail": [
            SegmentDefinition(
                name="High-Value Repeat Buyers",
                description="Loyalty candidates with strong engagement",
                rules=[
                    SegmentRule(field="lifecycle_stage", operator="equals", value="repeat buyer"),
                    SegmentRule(field="engagement_score", operator="greater_than", value="70"),
                ],
                logic="AND"
            ),
            SegmentDefinition(
                name="Cart Abandoners",
                description="Added to cart but did not purchase",
                rules=[
                    SegmentRule(field="behavioral_signals", operator="contains", value="added to cart"),
                ],
                logic="AND"
            ),
            SegmentDefinition(
                name="Lapsed Customers",
                description="Previously active, now dormant",
                rules=[
                    SegmentRule(field="lifecycle_stage", operator="equals", value="lapsed"),
                ],
                logic="AND"
            ),
        ],
    }
    return defaults.get(vertical, defaults["hr_software"])


def _to_zmp_payload(seg_id: str, seg: SegmentDefinition, vertical: str) -> dict:
    """Shape the segment into a ZMP-friendly structure."""
    return {
        "segment_id": seg_id,
        "segment_name": seg.name,
        "description": seg.description,
        "vertical": vertical,
        "logic": seg.logic,
        "rules": [r.model_dump() for r in seg.rules],
        "status": "draft",
        "source": "zeta-sandbox-foundry",
    }