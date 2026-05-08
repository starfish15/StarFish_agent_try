import os
import signal
import sys
import threading
from typing import Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent.core import Agent


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    history: list[dict[str, Any]]


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.agent = Agent()
        app.state.history = []
        yield

    app = FastAPI(title="StarFish Chat", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        text = req.text.strip()
        try:
            reply = app.state.agent.run(text)
        except Exception as exc:
            # 例如缺少 API Key 等错误，返回给客户端展示
            raise HTTPException(status_code=500, detail=str(exc))

        app.state.history.append({"role": "user", "content": text})
        app.state.history.append({"role": "assistant", "content": reply})

        return ChatResponse(reply=reply, history=app.state.history)

    @app.post("/shutdown")
    def shutdown() -> dict:
        # 以信号方式结束 uvicorn 进程（对本地桌面用途足够）
        def _kill() -> None:
            try:
                os.kill(os.getpid(), signal.SIGINT)
            except Exception:
                pass

        threading.Thread(target=_kill, daemon=True).start()
        return {"ok": True}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("CHAT_HOST", "0.0.0.0")
    port = int(os.getenv("CHAT_PORT", "8002"))
    uvicorn.run(app, host=host, port=port, log_level="info")
