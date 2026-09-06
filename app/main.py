"""FunnelIQ prediction API — Railway service.

Per the project's architecture decision, this service does prediction only:
it loads pre-trained .pkl models and serves predictions, never trains at
request time, and never touches Supabase with a service-role key. Auth and
data reads for the dashboard happen entirely client-side (static/index.html,
using the anon key + the signed-in user's session), so RLS is enforced by
Postgres itself.

Prediction endpoints, however, are gated here: each request's Supabase access
token is verified server-side (via Supabase's own /auth/v1/user check, using
only the public anon key -- never the service key) so a stranger who finds
this URL can't get predictions without ever signing in. This resolves the
"how does the API enforce auth" question left open in the architecture
decisions.
"""

import json
import os
from pathlib import Path

import httpx
import joblib
import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
MODELS_DIR = ROOT_DIR / "models"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

app = FastAPI(title="FunnelIQ API")

_ltv_model = joblib.load(MODELS_DIR / "ltv_regressor.pkl")
_ltv_meta = json.loads((MODELS_DIR / "ltv_regressor_meta.json").read_text())
_ltv_features = _ltv_meta["feature_columns"]


async def require_user(authorization: str | None = Header(default=None)) -> dict:
    """Verify the caller's Supabase session token. Raises 401 if missing/invalid."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return resp.json()


class LTVFeatures(BaseModel):
    ad_budget: float
    num_leads: float
    leads_answered: float
    leads_not_answered: float
    followup_1: float
    followup_2: float
    followup_3: float
    followup_4: float
    followup_5: float
    not_closed: float
    closed: float
    calls_to_closed: float
    calls_to_not_closed: float
    customer_acquisition_cost: float
    purchased: float


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/predict/ltv")
async def predict_ltv(features: LTVFeatures, user: dict = Depends(require_user)):
    row = pd.DataFrame([features.model_dump()])[_ltv_features]
    prediction = float(_ltv_model.predict(row)[0])
    return {
        "predicted_ltv_months": round(prediction, 1),
        "model": _ltv_meta["model_type"],
    }
