from fastapi import FastAPI

from .routers import auth, events, projects, teams
from .seed import seed

app = FastAPI(title="DOGFOOD Portal API")


@app.on_event("startup")
def on_startup():
    seed()


@app.get("/api/health")
def health():
    return {"ok": True}


app.include_router(auth.router)
app.include_router(events.router)
app.include_router(teams.router)
app.include_router(projects.router)
