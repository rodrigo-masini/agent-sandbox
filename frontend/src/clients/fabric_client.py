import os
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from openai import AsyncOpenAI
from dataclasses import dataclass
import httpx
import json
import time
from .base_client import BaseClient

@dataclass
class FabricConfig:
    api_key: str
    org_id: str
    project_id: str
    base_url: str = "https://api.telaos.com/v1"
    model: str = "wizard"
    timeout: int = 300
    max_retries: int = 3
    retry_delay: float = 1.0

class FabricClient(BaseClient):
    def __init__(self, config: FabricConfig):
        super().__init__(config.timeout, config.max_retries, config.retry_delay)
        self.config = config
        self.client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=httpx.Timeout(config.timeout),
            max_retries=config.max_retries,
        )
        self.headers = {
            "OpenAI-Organization": config.org_id,
            "OpenAI-Project": config.project_id,
        }

    async def chat_completion(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        stream: bool = False,
        **kwargs
    ) -> Dict:
        """Create a chat completion with enhanced error handling and metrics."""
        start_time = time.time()
        
        try:
            params = {
                "model": self.config.model,
                "messages": messages,
                "extra_headers": self.headers,
                "stream": stream,
                **kwargs
            }
            
            if tools:
                params["tools"] = tools
                params["tool_choice"] = tool_choice

            if stream:
                return await self._stream_completion(params)
            else:
                response = await self.client.chat.completions.create(**params)
                return self._format_response(response, time.time() - start_time)
                
        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            raise

    async def _stream_completion(self, params: Dict) -> AsyncGenerator[Dict, None]:
        """Handle streaming responses with proper error handling."""
        try:
            stream = await self.client.chat.completions.create(**params)
            async for chunk in stream:
                yield self._format_stream_chunk(chunk)
        except Exception as e:
            self.logger.error(f"Streaming failed: {e}")
            raise

    def _format_response(self, response, duration: float) -> Dict:
        """Format the response with additional metadata."""
        return {
            "choices": [
                {
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in (choice.message.tool_calls or [])
                        ] if choice.message.tool_calls else None
                    },
                    "finish_reason": choice.finish_reason
                } for choice in response.choices
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "metadata": {
                "duration": duration,
                "model": response.model,
                "id": response.id,
                "created": response.created
            }
        }

    def _format_stream_chunk(self, chunk) -> Dict:
        """Format streaming chunk with consistent structure."""
        choice = chunk.choices[0] if chunk.choices else None
        if not choice:
            return {"type": "chunk", "content": ""}
            
        delta = choice.delta
        return {
            "type": "chunk",
            "content": delta.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name if tc.function else None,
                        "arguments": tc.function.arguments if tc.function else None
                    }
                } for tc in (delta.tool_calls or [])
            ] if delta.tool_calls else None,
            "finish_reason": choice.finish_reason
        }

    async def health_check(self) -> Dict:
        """Check the health of the Fabric service."""
        try:
            response = await self.chat_completion([
                {"role": "user", "content": "Hello"}
            ], timeout=10)
            return {"status": "healthy", "response_time": response["metadata"]["duration"]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}