import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(tags=["images"])

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


class BuildImageRequest(BaseModel):
    brand_name: str = Field(..., example="Buffalo Wild Wings")
    campaign_theme: str = Field(..., example="loyalty reactivation, game-day season")
    tone: str = Field(..., example="energetic, warm, sports-focused")
    vertical: str = Field(..., example="retail")
    format: str = Field(
        "landscape",
        description="landscape, portrait, or square",
        example="landscape"
    )
    quality: str = Field(
        "medium",
        description="low, medium, or high",
        example="medium"
    )


@router.post(
    "/build-image",
    summary="Generate a campaign hero image",
    description=(
        "Fallback image generation via OpenAI gpt-image-1. "
        "Use native ZMP Image Generation capability first — "
        "only call this endpoint if native capability is unavailable or underperforms."
    )
)
async def build_image(req: BuildImageRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY not configured. Use native ZMP image generation instead."
        )

    size_map = {
        "landscape": "1792x1024",
        "portrait": "1024x1792",
        "square": "1024x1024",
    }
    size = size_map.get(req.format, "1792x1024")

    prompt = (
        f"Professional marketing email hero image for {req.brand_name}. "
        f"Campaign: {req.campaign_theme}. "
        f"Tone: {req.tone}. "
        f"Style: clean, modern, high-contrast, suitable for email header. "
        f"No text overlays. No logos. Brand-appropriate color palette."
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-image-1",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": req.quality,
            }
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Image generation failed: {response.text}"
        )

    data = response.json()
    image_url = data["data"][0].get("url", "")
    b64 = data["data"][0].get("b64_json", "")

    return {
        "brand_name": req.brand_name,
        "campaign_theme": req.campaign_theme,
        "format": req.format,
        "prompt_used": prompt,
        "image_url": image_url,
        "b64_json": b64,
        "note": "Use image_url to reference in ZMP template, or b64_json to upload directly",
    }
