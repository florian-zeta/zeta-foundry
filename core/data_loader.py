import json
import random
from pathlib import Path
from typing import Optional

DATA_PATH = Path(__file__).parent.parent / "data" / "base_profiles.jsonl"

# Loaded once at startup, held in memory
_profiles: list[dict] = []


def load_profiles() -> list[dict]:
    global _profiles
    if _profiles:
        return _profiles
    with open(DATA_PATH) as f:
        _profiles = [json.loads(line) for line in f if line.strip()]
    return _profiles


def get_identity_tier(profile: dict) -> str:
    """Classify each profile by how much Zeta can resolve them."""
    has_zync = bool(profile.get("zync_id"))
    has_md5 = bool(profile.get("email_md5_id"))
    if has_zync and has_md5:
        return "known"        # Full Data Cloud linkage
    elif has_md5:
        return "email-known"  # Email match only
    else:
        return "anonymous"    # Profile only, no identity resolution


# ── Vertical enrichment tables ──────────────────────────────────────────────
# These are the building blocks the /enhance-profiles endpoint draws from.
# Add new verticals here and the agent picks them up automatically.

VERTICALS = {
    "hr_software": {
        "industry": "Human Resources Technology",
        "company_sizes": ["50-200", "200-500", "500-2000", "2000+"],
        "job_titles": {
            "M": ["HR Director", "VP of People", "Head of Talent", "Chief People Officer", "HR Manager"],
            "F": ["HR Director", "VP of People", "Head of Talent", "Chief People Officer", "HR Manager"],
        },
        "pain_points": ["employee retention", "onboarding automation", "compliance reporting", "performance management"],
        "behavioral_signals": ["viewed pricing page", "downloaded whitepaper", "attended webinar", "requested demo"],
        "lifecycle_stages": ["awareness", "consideration", "evaluation", "decision"],
    },
    "retail": {
        "industry": "Retail & E-commerce",
        "company_sizes": ["1-10", "10-50", "50-200", "200-1000"],
        "job_titles": {
            "M": ["Marketing Manager", "VP Marketing", "Director of E-commerce", "Growth Lead", "CMO"],
            "F": ["Marketing Manager", "VP Marketing", "Director of E-commerce", "Growth Lead", "CMO"],
        },
        "pain_points": ["cart abandonment", "customer lifetime value", "seasonal campaigns", "loyalty programs"],
        "behavioral_signals": ["browsed product pages", "added to cart", "completed purchase", "opened email"],
        "lifecycle_stages": ["prospect", "first-time buyer", "repeat buyer", "lapsed", "loyal"],
    },
    "financial_services": {
        "industry": "Financial Services",
        "company_sizes": ["100-500", "500-2000", "2000-10000", "10000+"],
        "job_titles": {
            "M": ["VP Marketing", "Head of Digital", "Director of Acquisition", "CMO", "Marketing Director"],
            "F": ["VP Marketing", "Head of Digital", "Director of Acquisition", "CMO", "Marketing Director"],
        },
        "pain_points": ["compliance-safe messaging", "cross-sell opportunities", "churn prevention", "digital acquisition"],
        "behavioral_signals": ["viewed product page", "started application", "used calculator tool", "opened email"],
        "lifecycle_stages": ["prospect", "applicant", "new customer", "active", "at-risk", "churned"],
    },
    "healthcare": {
        "industry": "Healthcare & Life Sciences",
        "company_sizes": ["50-200", "200-1000", "1000-5000", "5000+"],
        "job_titles": {
            "M": ["Marketing Director", "VP Patient Engagement", "Head of Digital Health", "CMO", "Communications Manager"],
            "F": ["Marketing Director", "VP Patient Engagement", "Head of Digital Health", "CMO", "Communications Manager"],
        },
        "pain_points": ["patient engagement", "appointment adherence", "care gap closure", "HIPAA-safe outreach"],
        "behavioral_signals": ["visited health topic page", "booked appointment", "completed survey", "engaged with portal"],
        "lifecycle_stages": ["prospect", "new patient", "active patient", "lapsed patient", "high-risk"],
    },
}


def get_vertical(name: str) -> dict:
    """Return vertical config, defaulting to hr_software if unknown."""
    return VERTICALS.get(name.lower().replace(" ", "_"), VERTICALS["hr_software"])


def enhance_profile(profile: dict, vertical_config: dict, icp: Optional[dict] = None) -> dict:
    """
    Inject vertical-specific attributes into a base profile.
    Returns a new dict — never mutates the original.
    """
    enhanced = profile.copy()
    gender = profile.get("gender", "M")
    rng = random.Random(profile.get("user_id", ""))  # deterministic per profile

    # Identity tier (preserved as-is — realistic data quality)
    enhanced["identity_tier"] = get_identity_tier(profile)

    # Job / firmographic enrichment
    enhanced["job_title"] = rng.choice(vertical_config["job_titles"].get(gender, vertical_config["job_titles"]["M"]))
    enhanced["industry"] = vertical_config["industry"]
    enhanced["company_size"] = rng.choice(vertical_config["company_sizes"])

    # Behavioral signals (2-3 per profile, realistic spread)
    signals = vertical_config["behavioral_signals"]
    n_signals = rng.randint(1, min(3, len(signals)))
    enhanced["behavioral_signals"] = rng.sample(signals, n_signals)

    # Lifecycle stage
    enhanced["lifecycle_stage"] = rng.choice(vertical_config["lifecycle_stages"])

    # Pain point affinity (1 per profile)
    enhanced["pain_point_affinity"] = rng.choice(vertical_config["pain_points"])

    # Engagement score (0-100, weighted toward middle)
    enhanced["engagement_score"] = int(rng.gauss(55, 20))
    enhanced["engagement_score"] = max(0, min(100, enhanced["engagement_score"]))

    # ICP match flag (if ICP params were passed)
    if icp:
        enhanced["icp_match"] = _score_icp_match(enhanced, icp)

    return enhanced


def _score_icp_match(profile: dict, icp: dict) -> bool:
    """Simple ICP scoring — expand this as needed."""
    score = 0
    if icp.get("target_states") and profile.get("state") in icp["target_states"]:
        score += 1
    if icp.get("target_titles") and any(t.lower() in profile.get("job_title", "").lower() for t in icp["target_titles"]):
        score += 2
    if icp.get("min_engagement") and profile.get("engagement_score", 0) >= icp["min_engagement"]:
        score += 1
    return score >= 2
