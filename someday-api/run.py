import uvicorn
from config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_ENV == "dev",
        log_level="warning",  # uvicorn's own logs stay quiet; ours handle everything
    )
