"""FunnelIQ prediction API — Railway skeleton.

Per the project's architecture decision, this service does prediction only:
it loads pre-trained .pkl models and serves predictions, never trains at
request time, and never touches Supabase with a service-role key. Auth and
data reads happen entirely client-side (static/index.html, using the anon
key + the signed-in user's session), so RLS is enforced by Postgres itself,
not by this API.

Deliberately minimal for now (Packages 2-6 aren't built yet) — the brief's
own advice is to get this skeleton deployed and healthy before adding real
endpoints.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="FunnelIQ API")


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "healthy"}
