from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import status, profiles, load_audience, build_resources, build_events
from routers import build_snippets, build_template, build_campaign, resource_schema

app = FastAPI(
    title="Zeta Sandbox Foundry",
    description="Asset generation foundry for ZMP sandbox population",
    version="1.0.0",
    servers=[{"url": "https://web-production-9ea5b.up.railway.app"}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status.router)
app.include_router(profiles.router)
app.include_router(load_audience.router)
app.include_router(build_resources.router)
app.include_router(build_events.router)
app.include_router(build_snippets.router)
app.include_router(build_template.router)
app.include_router(build_campaign.router)
app.include_router(resource_schema.router)