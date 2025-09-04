import os
import asyncio
from typing import Dict, List, Optional, Any
import httpx
import json
import time
from .base_client import BaseClient

class AgtsdbxClient(BaseClient):
    def __init__(self, base_url: str = None, timeout: int = 300):
        super().__init__(timeout)
        self.base_url = base_url or os.getenv("AGTSDBX_BASE_URL", "http://localhost:8000")
        self.session = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def execute_command(
        self,
        command: str,
        options: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict:
        """Execute a shell command with enhanced options and error handling."""
        payload = {
            "command": command,
            "guideFollowed": True,
            "options": options or {}
        }
        
        start_time = time.time()
        
        try:
            response = await self._make_request(
                "POST", 
                "/api/v1/exec", 
                json=payload,
                timeout=timeout or self.timeout
            )
            
            duration = time.time() - start_time
            
            return {
                **response,
                "metadata": {
                    "duration": duration,
                    "command": command,
                    "timestamp": time.time()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            raise

    async def write_file(
        self,
        file_path: str,
        content: str,
        options: Optional[Dict] = None
    ) -> Dict:
        """Write content to a file with enhanced options."""
        payload = {
            "filePath": file_path,
            "content": content,
            "options": options or {}
        }
        
        try:
            response = await self._make_request("POST", "/api/v1/file/write", json=payload)
            return response
        except Exception as e:
            self.logger.error(f"File write failed: {e}")
            raise

    async def read_file(
        self,
        file_path: str,
        options: Optional[Dict] = None
    ) -> Dict:
        """Read file content with enhanced options."""
        payload = {
            "filePath": file_path,
            "options": options or {}
        }
        
        try:
            response = await self._make_request("POST", "/api/v1/file/read", json=payload)
            return response
        except Exception as e:
            self.logger.error(f"File read failed: {e}")
            raise

    async def list_files(
        self,
        path: str = ".",
        options: Optional[Dict] = None
    ) -> Dict:
        """List files in a directory with enhanced filtering options."""
        payload = {
            "path": path,
            "options": options or {}
        }
        
        try:
            response = await self._make_request("POST", "/api/v1/file/list", json=payload)
            return response
        except Exception as e:
            self.logger.error(f"File listing failed: {e}")
            raise

    async def delete_file(self, file_path: str) -> Dict:
        """Delete a file or directory."""
        payload = {"filePath": file_path}
        
        try:
            response = await self._make_request("DELETE", "/api/v1/file/delete", json=payload)
            return response
        except Exception as e:
            self.logger.error(f"File deletion failed: {e}")
            raise

    async def get_system_info(self) -> Dict:
        """Get system information and metrics."""
        try:
            response = await self._make_request("GET", "/api/v1/system/info")
            return response
        except Exception as e:
            self.logger.error(f"System info retrieval failed: {e}")
            raise

    async def get_metrics(self) -> Dict:
        """Get system metrics and performance data."""
        try:
            response = await self._make_request("GET", "/api/v1/system/metrics")
            return response
        except Exception as e:
            self.logger.error(f"Metrics retrieval failed: {e}")
            raise

    async def docker_run(
        self,
        image: str,
        command: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Dict:
        """Run a Docker container."""
        payload = {
            "image": image,
            "command": command,
            "options": options or {}
        }
        
        try:
            response = await self._make_request("POST", "/api/v1/docker/run", json=payload)
            return response
        except Exception as e:
            self.logger.error(f"Docker run failed: {e}")
            raise

    async def docker_list(self) -> Dict:
        """List Docker containers."""
        try:
            response = await self._make_request("GET", "/api/v1/docker/list")
            return response
        except Exception as e:
            self.logger.error(f"Docker list failed: {e}")
            raise

    async def network_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        data: Optional[Any] = None,
        options: Optional[Dict] = None
    ) -> Dict:
        """Make a network request through Agtsdbx."""
        payload = {
            "url": url,
            "method": method,
            "headers": headers or {},
            "data": data,
            "options": options or {}
        }
        
        try:
            response = await self._make_request("POST", "/api/v1/network/request", json=payload)
            return response
        except Exception as e:
            self.logger.error(f"Network request failed: {e}")
            raise

    async def health_check(self) -> Dict:
        """Check Agtsdbx service health."""
        try:
            response = await self._make_request("GET", "/health", timeout=10)
            return {"status": "healthy", **response}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Dict:
        """Make an HTTP request with retry logic and error handling."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = await self.session.request(
                    method,
                    url,
                    timeout=timeout or self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                
                if response.headers.get("content-type", "").startswith("application/json"):
                    return response.json()
                else:
                    return {"content": response.text}
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500 or attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))