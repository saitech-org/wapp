# Minimal application entrypoint template for a Wapp demo project.
# Copy this to your project root with `wapp-init`.

from automigrate import lifespan_with_subprocess
from users_demo import UsersWapp
from settings import DB_URL_ASYNC
from wapp.core.asgi import make_app

# Create the app directly from the UsersWapp exported by users_demo
app = make_app(UsersWapp, db_url=DB_URL_ASYNC, title="Wapp Users Demo API", lifespan=lifespan_with_subprocess)

# Optional: simple health endpoint

@app.get("/health")
async def _health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
