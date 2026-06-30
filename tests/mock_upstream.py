"""一个假的 OpenAI 兼容上游，用于端到端测试（不需要真实 key/网络）。"""
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


def build_mock_app() -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        auth = request.headers.get("authorization", "")
        key = auth[7:] if auth.lower().startswith("bearer ") else ""
        body = await request.json()
        model = body.get("model")

        # 用坏 key 模拟上游 500，用于测试故障转移
        if key == "BAD_KEY":
            return JSONResponse(status_code=500, content={"error": "bad key"})

        if body.get("stream"):
            async def gen():
                for piece in ["Hello", " world"]:
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': piece}}]})}\n\n".encode()
                # 末尾 usage 块（OpenAI 在 include_usage 时返回）
                yield f"data: {json.dumps({'choices': [], 'usage': {'prompt_tokens': 4, 'completion_tokens': 3, 'total_tokens': 7}})}\n\n".encode()
                yield b"data: [DONE]\n\n"
            return StreamingResponse(gen(), media_type="text/event-stream")

        return JSONResponse(content={
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": f"echo:{model}"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        })

    return app
