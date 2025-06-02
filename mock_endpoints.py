"""
Mock endpoints for local testing without API keys
"""
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import json


def add_mock_endpoints(app: FastAPI):
    """Add mock API endpoints for testing without real API keys"""
    
    @app.post("/mock/v1/chat/completions")
    async def mock_chat_completions(request: Request):
        """Mock OpenAI-compatible chat completions endpoint"""
        body = await request.json()
        
        messages = body.get("messages", [])
        model = body.get("model", "mock-model")
        stream = body.get("stream", False)
        
        # Get the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # Generate a simple response
        if model == "echo-model":
            response_content = f"Echo: {user_message}"
        else:
            response_content = f"This is a mock response from {model}. You said: '{user_message}'"
        
        if stream:
            # Return streaming response
            def generate():
                # Initial chunk
                chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"role": "assistant", "content": ""},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                
                # Content chunks
                words = response_content.split()
                for word in words:
                    chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": word + " "},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    time.sleep(0.05)  # Simulate typing delay
                
                # Final chunk
                final_chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            # Return non-streaming response
            response = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(user_message.split()),
                    "completion_tokens": len(response_content.split()),
                    "total_tokens": len(user_message.split()) + len(response_content.split())
                }
            }
            return JSONResponse(content=response)
    
    @app.get("/mock/v1/models")
    async def mock_models():
        """Mock models endpoint"""
        return JSONResponse(content={
            "object": "list",
            "data": [
                {
                    "id": "echo-model",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "mock"
                },
                {
                    "id": "demo-model",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "mock"
                }
            ]
        })