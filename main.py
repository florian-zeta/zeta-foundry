from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import profiles, segments, html_builder, status, images, campaign, load_audience, resource_schema, build_resources

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
app.include_router(segments.router)
app.include_router(html_builder.router)
app.include_router(images.router)
app.include_router(campaign.router)
app.include_router(load_audience.router)
app.include_router(resource_schema.router)
app.include_router(build_resources.router)