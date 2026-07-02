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

    @app.post("/v1/embeddings")
    async def embeddings(request: Request):
        body = await request.json()
        inp = body.get("input")
        n = len(inp) if isinstance(inp, list) else 1
        return JSONResponse(content={
            "object": "list",
            "data": [{"object": "embedding", "index": i, "embedding": [0.1, 0.2, 0.3]}
                     for i in range(n)],
            "model": body.get("model"),
            "usage": {"prompt_tokens": 6, "total_tokens": 6},
        })

    # ---- Anthropic 原生 Messages ----
    @app.post("/v1/messages")
    async def anthropic_messages(request: Request):
        body = await request.json()
        model = body.get("model")
        if body.get("stream"):
            async def gen():
                yield b'event: message_start\ndata: {"type":"message_start","message":{"usage":{"input_tokens":4}}}\n\n'
                yield b'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hi"}}\n\n'
                yield b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":2}}\n\n'
                yield b'event: message_stop\ndata: {"type":"message_stop"}\n\n'
            return StreamingResponse(gen(), media_type="text/event-stream")
        return JSONResponse(content={
            "id": "msg_mock",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": f"claude-echo:{model}"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 3},
        })

    # ---- Gemini 原生 ----
    @app.post("/v1beta/models/{model_verb:path}")
    async def gemini(model_verb: str, request: Request):
        body = await request.json()
        model = model_verb.split(":")[0]
        text = f"gemini-echo:{model}"
        return JSONResponse(content={
            "candidates": [{
                "content": {"role": "model", "parts": [{"text": text}]},
                "finishReason": "STOP",
            }],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 3, "totalTokenCount": 8},
            "modelVersion": model,
        })

    return app
