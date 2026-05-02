from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

router = APIRouter(tags=["html"])

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


class BrandTokens(BaseModel):
    primary_color: str = Field("#1a1a2e", example="#1a1a2e")
    accent_color: str = Field("#e94560", example="#e94560")
    font_family: str = Field("Arial, sans-serif", example="Arial, sans-serif")
    logo_text: str = Field("YourBrand", description="Text fallback if no logo URL")
    logo_url: Optional[str] = Field(None, description="URL to brand logo image")


class BuildHTMLRequest(BaseModel):
    template_id: str = Field(
        "email_hero",
        description="Which template to render. Options: email_hero, email_nurture",
        example="email_hero"
    )
    brand: BrandTokens = Field(default_factory=BrandTokens)
    subject_line: str = Field(..., example="Your Q4 HR strategy starts here")
    preview_text: str = Field(..., example="See how leading companies are solving retention")
    headline: str = Field(..., example="Stop losing great people to preventable problems")
    body_copy: str = Field(
        ...,
        example="HR Directors at companies like yours are using smarter data to reduce attrition by 30%."
    )
    cta_text: str = Field(..., example="See the platform")
    cta_url: str = Field("https://example.com", example="https://example.com")
    vertical: str = Field("hr_software", example="hr_software")
    campaign_theme: Optional[str] = Field(None, example="Q4 pipeline push")


@router.post(
    "/build-html",
    summary="Render a ZMP-ready HTML email template",
    description=(
        "Injects brand tokens and copy into a ZMP-safe HTML email template. "
        "Returns the rendered HTML string ready to paste into ZMP template editor."
    )
)
def build_html(req: BuildHTMLRequest):
    template_name = f"{req.template_id}.html"

    try:
        template = jinja_env.get_template(template_name)
    except Exception:
        # Fallback to default if template not found
        template = jinja_env.get_template("email_hero.html")

    rendered = template.render(
        brand=req.brand.dict(),
        subject_line=req.subject_line,
        preview_text=req.preview_text,
        headline=req.headline,
        body_copy=req.body_copy,
        cta_text=req.cta_text,
        cta_url=req.cta_url,
        vertical=req.vertical,
        campaign_theme=req.campaign_theme or "",
    )

    return {
        "template_id": req.template_id,
        "vertical": req.vertical,
        "subject_line": req.subject_line,
        "html": rendered,
        "char_count": len(rendered),
        "note": "Paste html value directly into ZMP template editor",
    }
