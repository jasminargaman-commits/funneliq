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

_upsell_model = joblib.load(MODELS_DIR / "upsell_classifier.pkl")
_upsell_meta = json.loads((MODELS_DIR / "upsell_classifier_meta.json").read_text())
_upsell_features = _upsell_meta["feature_columns"]

_super_model = joblib.load(MODELS_DIR / "super_customer_classifier.pkl")
_super_meta = json.loads((MODELS_DIR / "super_customer_classifier_meta.json").read_text())
_super_features = _super_meta["feature_columns"]

_profit_model = joblib.load(MODELS_DIR / "profit_regressor.pkl")
_profit_meta = json.loads((MODELS_DIR / "profit_regressor_meta.json").read_text())
_profit_features = _profit_meta["feature_columns"]
_budget_profiles = json.loads((MODELS_DIR / "budget_profiles.json").read_text())


def _budget_tier(ad_budget: float) -> str:
    """Must match the thresholds used to train models/super_customer_classifier.pkl."""
    if ad_budget <= 1500:
        return "Low"
    elif ad_budget <= 5000:
        return "Mid"
    return "High"


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


class UpsellFeatures(BaseModel):
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


class SuperCustomerFeatures(BaseModel):
    ad_budget: float
    num_leads: float
    leads_answered: float
    leads_not_answered: float


class Campaign(BaseModel):
    ad_budget: int
    count: int


class BudgetStrategy(BaseModel):
    campaigns: list[Campaign]


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


@app.post("/predict/upsell")
async def predict_upsell(features: UpsellFeatures, user: dict = Depends(require_user)):
    """Only meaningful for a customer who has already purchased -- see the Package 3
    leakage decision (models/upsell_classifier_meta.json: row_filter = purchased == 1)."""
    row = pd.DataFrame([features.model_dump()])[_upsell_features]
    probability = float(_upsell_model.predict_proba(row)[0][1])
    return {
        "upsell_probability": round(probability, 3),
        "predicted_upsell": probability >= 0.5,
        "model": _upsell_meta["model_type"],
    }


@app.post("/predict/super_customer")
async def predict_super_customer(features: SuperCustomerFeatures, user: dict = Depends(require_user)):
    """Early-funnel only, per the Package 4 leakage decision (the strictest package -- see
    models/super_customer_classifier_meta.json). Only meaningful for purchased==1 customers."""
    row = features.model_dump()
    row["budget_tier"] = _budget_tier(row["ad_budget"])
    row = pd.DataFrame([row])[_super_features]
    probability = float(_super_model.predict_proba(row)[0][1])
    return {
        "super_customer_score": round(probability * 100, 1),
        "model": _super_meta["model_type"],
    }


def _expected_profit_for_campaign(ad_budget: int) -> float:
    key = str(ad_budget)
    if key not in _budget_profiles:
        supported = ", ".join(sorted(_budget_profiles, key=int))
        raise HTTPException(
            status_code=422,
            detail=f"ad_budget must be one of the budget levels this data covers: {supported}",
        )
    profile = _budget_profiles[key]
    row = pd.DataFrame([profile["typical_profile"]])[_profit_features]
    predicted_profit_if_purchased = float(_profit_model.predict(row)[0])
    return profile["purchase_rate"] * predicted_profit_if_purchased


@app.post("/simulate/budget")
async def simulate_budget(strategy: BudgetStrategy, user: dict = Depends(require_user)):
    """Portfolio-level simulator, not a single-customer prediction -- see the Package 6
    leakage decision (full-funnel model + typical-profile-per-budget imputation,
    models/profit_regressor_meta.json / models/budget_profiles.json)."""
    breakdown = []
    total_spend = 0
    total_profit = 0.0
    for campaign in strategy.campaigns:
        per_campaign_profit = _expected_profit_for_campaign(campaign.ad_budget)
        campaign_total_profit = per_campaign_profit * campaign.count
        campaign_total_spend = campaign.ad_budget * campaign.count
        breakdown.append({
            "ad_budget": campaign.ad_budget,
            "count": campaign.count,
            "expected_profit_per_campaign": round(per_campaign_profit, 0),
            "expected_total_profit": round(campaign_total_profit, 0),
        })
        total_spend += campaign_total_spend
        total_profit += campaign_total_profit

    return {
        "breakdown": breakdown,
        "total_spend": total_spend,
        "total_expected_profit": round(total_profit, 0),
        "model": _profit_meta["model_type"],
    }
