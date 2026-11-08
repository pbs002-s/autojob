"""FastAPI app factory: wires auth, workspaces, API routers and static pages."""
import asyncio
import contextlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api import agent, inbox, jobs, profile, public, users
from src.auth import routes as auth_routes
from src.auth.security import MIN_PASSWORD_LENGTH
from src.auth.store import AuthStore
from src.workspace import Workspace, seed_demo

from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger(__name__)
UI_DIR = Path("ui")
DEMO_RESET_SECONDS = 30 * 60


@dataclass(frozen=True)
class Settings:
    data_dir: str = "data"
    profile_path: str = "config/profile.json"
    demo_enabled: bool = False
    admin_email: str = ""
    admin_password: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            demo_enabled=os.getenv("AUTOJOB_DEMO", "0") == "1",
            admin_email=os.getenv("AUTOJOB_ADMIN_EMAIL", ""),
            admin_password=os.getenv("AUTOJOB_ADMIN_PASSWORD", ""),
        )


def _bootstrap_admin(auth: AuthStore, settings: Settings) -> None:
    if auth.count_admins() > 0:
        return
    if not settings.admin_email or len(settings.admin_password) < MIN_PASSWORD_LENGTH:
        raise RuntimeError(
            "No admin user exists. Set AUTOJOB_ADMIN_EMAIL and AUTOJOB_ADMIN_PASSWORD "
            f"(min {MIN_PASSWORD_LENGTH} chars) in .env, then restart."
        )
    if auth.get_user_by_email(settings.admin_email):
        raise RuntimeError(f"{settings.admin_email} exists but is not an active admin; fix it in the users table.")
    auth.create_user(settings.admin_email, settings.admin_password, "admin")
    log.warning("Created first admin user %s", settings.admin_email)


def _new_demo_workspace(settings: Settings) -> Workspace:
    db_path = str(Path(settings.data_dir) / "demo.db")
    profile_path = str(Path(settings.data_dir) / "demo_profile.json")
    seed_demo(db_path, profile_path)
    return Workspace(db_path, profile_path, demo=True)


async def _demo_reset_loop(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(DEMO_RESET_SECONDS)
        app.state.demo_workspace.controller.stop()
        app.state.demo_workspace = _new_demo_workspace(app.state.settings)


def _error_envelope(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"success": False, "error": message})


def create_app(settings: Settings = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        reset_task = asyncio.create_task(_demo_reset_loop(app)) if settings.demo_enabled else None
        yield
        if reset_task:
            reset_task.cancel()
        app.state.real_workspace.controller.stop()

    app = FastAPI(title="AutoJob AI", version="2.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.auth = AuthStore(str(Path(settings.data_dir) / "autojob.db"))
    _bootstrap_admin(app.state.auth, settings)
    app.state.real_workspace = Workspace(str(Path(settings.data_dir) / "autojob.db"), settings.profile_path)
    app.state.demo_workspace = _new_demo_workspace(settings) if settings.demo_enabled else None

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return _error_envelope(exc.status_code, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = [".".join(str(x) for x in e["loc"][1:]) or "body" for e in exc.errors()]
        return _error_envelope(422, f"Invalid input: {', '.join(fields)}")

    for module in (auth_routes, agent, jobs, inbox, profile, users, public):
        app.include_router(module.router)

    @app.get("/api/{rest:path}", include_in_schema=False)
    def api_not_found(rest: str):
        raise HTTPException(status_code=404, detail="Not found.")

    app.mount("/assets", StaticFiles(directory=UI_DIR), name="assets")

    @app.get("/", include_in_schema=False)
    def landing():
        return FileResponse(UI_DIR / "landing" / "index.html")

    @app.get("/login", include_in_schema=False)
    def login_page():
        return FileResponse(UI_DIR / "login" / "index.html")

    @app.get("/app", include_in_schema=False)
    @app.get("/app/{path:path}", include_in_schema=False)
    def app_shell(path: str = ""):
        return FileResponse(UI_DIR / "app" / "index.html")

    return app


def start_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn
    app = create_app()
    print(f"\n[AutoJob] Console at http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    start_server()
