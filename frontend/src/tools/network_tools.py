# ==============================================
# NETWORK TOOLS IMPLEMENTATION
# ==============================================

from typing import Dict, List

from .base_tool import BaseTool


class NetworkTools(BaseTool):
    """Network operation tools."""

    def get_tool_definitions(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "http_request",
                    "description": "Make an HTTP request to a URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to request"},
                            "method": {
                                "type": "string",
                                "enum": [
                                    "GET",
                                    "POST",
                                    "PUT",
                                    "DELETE",
                                    "PATCH",
                                    "HEAD",
                                ],
                                "description": "HTTP method",
                                "default": "GET",
                            },
                            "headers": {
                                "type": "object",
                                "description": "Request headers",
                                "default": {},
                            },
                            "data": {
                                "type": "string",
                                "description": "Request body data",
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Request timeout in seconds",
                                "default": 30,
                            },
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "download_file",
                    "description": "Download a file from a URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to download from",
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path to save the downloaded file",
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Download timeout in seconds",
                                "default": 300,
                            },
                        },
                        "required": ["url", "output_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_port",
                    "description": "Check if a port is open on a host.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host": {
                                "type": "string",
                                "description": "Hostname or IP address",
                            },
                            "port": {
                                "type": "integer",
                                "description": "Port number to check",
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Connection timeout in seconds",
                                "default": 5,
                            },
                        },
                        "required": ["host", "port"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "dns_lookup",
                    "description": "Perform DNS lookup for a domain.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domain": {
                                "type": "string",
                                "description": "Domain name to lookup",
                            },
                            "record_type": {
                                "type": "string",
                                "enum": ["A", "AAAA", "MX", "TXT", "NS", "CNAME"],
                                "description": "DNS record type",
                                "default": "A",
                            },
                        },
                        "required": ["domain"],
                    },
                },
            },
        ]

    async def http_request(self, **kwargs) -> str:
        """Make an HTTP request."""
        try:
            url = kwargs.get("url")
            method = kwargs.get("method", "GET")
            headers = kwargs.get("headers", {})
            data = kwargs.get("data", None)
            timeout = kwargs.get("timeout", 30)

            async with self.agtsdbx_client as client:
                result = await client.network_request(
                    url, method, headers, data, {"timeout": timeout}
                )

            if result.get("success"):
                response_data = result.get("data", {})
                status = response_data.get("status_code", "unknown")
                body = response_data.get("body", "")

                return (
                    f"HTTP {method} {url}\nStatus: {status}\n\nResponse:\n{body[:1000]}"
                )
            else:
                return f"Request failed: {result.get('error', 'Unknown error')}"

        except Exception as e:
            return f"Error making HTTP request: {str(e)}"

    async def download_file(self, **kwargs) -> str:
        """Download a file from URL."""
        try:
            url = kwargs.get("url")
            output_path = kwargs.get("output_path")
            timeout = kwargs.get("timeout", 300)

            command = f"curl -L -o {output_path} --max-time {timeout} {url}"

            async with self.agtsdbx_client as client:
                result = await client.execute_command(
                    command, {"timeout": timeout + 10}
                )

            if result.get("exit_code", 0) == 0:
                return f"Successfully downloaded file to: {output_path}"
            else:
                return f"Download failed: {result.get('stderr', 'Unknown error')}"

        except Exception as e:
            return f"Error downloading file: {str(e)}"

    async def check_port(self, **kwargs) -> str:
        """Check if a port is open."""
        try:
            host = kwargs.get("host")
            port = kwargs.get("port")
            timeout = kwargs.get("timeout", 5)

            command = f"timeout {timeout} nc -zv {host} {port}"

            async with self.agtsdbx_client as client:
                result = await client.execute_command(command, {"timeout": timeout + 2})

            if result.get("exit_code", 0) == 0:
                return f"Port {port} on {host} is OPEN"
            else:
                return f"Port {port} on {host} is CLOSED or unreachable"

        except Exception as e:
            return f"Error checking port: {str(e)}"

    async def dns_lookup(self, **kwargs) -> str:
        """Perform DNS lookup."""
        try:
            domain = kwargs.get("domain")
            record_type = kwargs.get("record_type", "A")

            command = f"dig +short {domain} {record_type}"

            async with self.agtsdbx_client as client:
                result = await client.execute_command(command, {"timeout": 10})

            if result.get("exit_code", 0) == 0:
                output = result.get("stdout", "No records found").strip()
                if output:
                    return f"DNS lookup for {domain} ({record_type} records):\n{output}"
                else:
                    return f"No {record_type} records found for {domain}"
            else:
                return f"DNS lookup failed: {result.get('stderr', 'Unknown error')}"

        except Exception as e:
            return f"Error performing DNS lookup: {str(e)}"
