"""FunnelIQ prediction API — Railway skeleton.

Per the project's architecture decision, this service does prediction only:
it loads pre-trained .pkl models and serves predictions, never trains at
request time, and never touches Supabase with a service-role key. Auth and
data live in Supabase; this API stays dumb and restart-safe.

Deliberately minimal for now (Packages 2-6 aren't built yet) — the brief's
own advice is to get this skeleton deployed and healthy before adding real
endpoints.
"""

from fastapi import FastAPI

app = FastAPI(title="FunnelIQ API")


@app.get("/")
def root():
    return {"service": "funneliq-api", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}
