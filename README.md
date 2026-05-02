# Zeta Sandbox Foundry

A FastAPI service that populates ZMP sandboxes on demand. The ZMP agent calls this via OpenAPI 3.0 actions — send a brief, get back enhanced profiles, segments, and email templates ready to load into ZMP.

---

## What it does

| Endpoint | What it returns |
|---|---|
| `GET /status` | Foundry health + data inventory |
| `POST /enhance-profiles` | 1,064 base profiles enhanced with vertical attributes |
| `POST /build-segments` | ZMP-ready segment definitions |
| `POST /build-html` | Rendered HTML email template |

---

## Run locally (first time)

**1. Make sure you have Python 3.11+**
```bash
python --version
```

**2. Create a virtual environment**
```bash
cd zeta-foundry
python -m venv venv
source venv/bin/activate       # Mac/Linux
# venv\Scripts\activate        # Windows
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Start the server**
```bash
uvicorn main:app --reload
```

**5. Open the interactive docs**
Visit: http://localhost:8000/docs

You should see all endpoints listed and be able to test them right in the browser.

---

## Deploy to Railway (one click)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select this repo — Railway auto-detects Python and uses `railway.toml`
4. Once deployed, copy the public URL (looks like `https://zeta-foundry-production.up.railway.app`)

That URL is your foundry base URL for the ZMP agent action.

---

## Register as a ZMP Agent Action

Once deployed, ZMP needs to know about your foundry endpoints.

1. In ZMP, go to **Agent Builder → Actions → Add Action**
2. Select **OpenAPI 3.0**
3. Enter your foundry URL + `/openapi.json` — e.g. `https://your-foundry.up.railway.app/openapi.json`
4. ZMP will auto-import all endpoints as callable actions

The agent can then call `/enhance-profiles`, `/build-segments`, and `/build-html` directly from a conversation.

---

## Quick test (curl)

```bash
# Health check
curl https://your-foundry.up.railway.app/status

# Enhance 50 HR software profiles
curl -X POST https://your-foundry.up.railway.app/enhance-profiles \
  -H "Content-Type: application/json" \
  -d '{"vertical": "hr_software", "count": 50}'

# Build default segments
curl -X POST https://your-foundry.up.railway.app/build-segments \
  -H "Content-Type: application/json" \
  -d '{"vertical": "hr_software", "campaign_theme": "Q4 pipeline push"}'
```

---

## Adding a new vertical

Open `core/data_loader.py` and add an entry to the `VERTICALS` dict following the same structure as `hr_software`. The agent picks it up automatically — no other changes needed.

---

## Project structure

```
zeta-foundry/
├── main.py                    # App entry point
├── requirements.txt
├── railway.toml               # Railway deploy config
├── Procfile                   # Fallback deploy config
├── data/
│   └── base_profiles.jsonl    # 1,064 base contact records
├── core/
│   └── data_loader.py         # Profile loading + enhancement logic
├── routers/
│   ├── status.py              # GET /status
│   ├── profiles.py            # POST /enhance-profiles
│   ├── segments.py            # POST /build-segments
│   └── html_builder.py        # POST /build-html
└── templates/
    ├── email_hero.html        # Bold hero email template
    └── email_nurture.html     # Conversational nurture template
```
