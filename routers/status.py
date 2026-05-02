from fastapi import APIRouter
from core.data_loader import load_profiles, get_identity_tier, VERTICALS

router = APIRouter(tags=["status"])


@router.get("/", summary="Health check")
def root():
    return {"status": "ok", "service": "Zeta Sandbox Foundry"}


@router.get("/status", summary="Foundry status and inventory")
def status():
    profiles = load_profiles()

    # Identity tier breakdown
    tiers = {"known": 0, "email-known": 0, "anonymous": 0}
    for p in profiles:
        tiers[get_identity_tier(p)] += 1

    return {
        "status": "ready",
        "base_profiles": len(profiles),
        "identity_tiers": tiers,
        "available_verticals": list(VERTICALS.keys()),
        "endpoints": [
            "POST /enhance-profiles",
            "POST /build-segments",
            "POST /build-html",
        ],
    }
