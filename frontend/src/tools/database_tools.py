# ==============================================
# DATABASE TOOLS IMPLEMENTATION
# ==============================================

from typing import Dict, List

from .base_tool import BaseTool


class DatabaseTools(BaseTool):
    """Database operation tools."""

    def get_tool_definitions(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "execute_sql",
                    "description": "Execute SQL query on a database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "database_type": {
                                "type": "string",
                                "enum": ["sqlite", "postgresql", "mysql"],
                                "description": "Type of database",
                            },
                            "connection_string": {
                                "type": "string",
                                "description": (
                                    "Database connection string or file path for SQLite"
                                ),
                            },
                            "query": {
                                "type": "string",
                                "description": "SQL query to execute",
                            },
                            "fetch": {
                                "type": "boolean",
                                "description": (
                                    "Whether to fetch results (for SELECT queries)"
                                ),
                                "default": True,
                            },
                        },
                        "required": ["database_type", "connection_string", "query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "backup_database",
                    "description": "Create a backup of a database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "database_type": {
                                "type": "string",
                                "enum": ["sqlite", "postgresql", "mysql"],
                                "description": "Type of database",
                            },
                            "source": {
                                "type": "string",
                                "description": "Source database path or connection",
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path for backup file",
                            },
                        },
                        "required": ["database_type", "source", "output_path"],
                    },
                },
            },
        ]

    async def execute_sql(self, **kwargs) -> str:
        """Execute SQL query."""
        try:
            database_type = kwargs.get("database_type")
            connection_string = kwargs.get("connection_string")
            query = kwargs.get("query")
            # The 'fetch' variable was assigned but never used, so it is removed.

            # For SQLite (as example)
            if database_type == "sqlite":
                command = f'sqlite3 {connection_string} "{query}"'
            elif database_type == "postgresql":
                command = f'psql {connection_string} -c "{query}"'
            elif database_type == "mysql":
                command = f'mysql {connection_string} -e "{query}"'
            else:
                return f"Unsupported database type: {database_type}"

            async with self.agtsdbx_client as client:
                result = await client.execute_command(command, {"timeout": 60})

            if result.get("exit_code", 0) == 0:
                output = result.get("stdout", "Query executed successfully")
                return f"SQL Query Result:\n{output}"
            else:
                return f"Query failed: {result.get('stderr', 'Unknown error')}"

        except Exception as e:
            return f"Error executing SQL: {str(e)}"

    async def backup_database(self, **kwargs) -> str:
        """Backup a database."""
        try:
            database_type = kwargs.get("database_type")
            source = kwargs.get("source")
            output_path = kwargs.get("output_path")

            if database_type == "sqlite":
                command = f"sqlite3 {source} '.backup {output_path}'"
            elif database_type == "postgresql":
                command = f"pg_dump {source} > {output_path}"
            elif database_type == "mysql":
                command = f"mysqldump {source} > {output_path}"
            else:
                return f"Unsupported database type: {database_type}"

            async with self.agtsdbx_client as client:
                result = await client.execute_command(command, {"timeout": 300})

            if result.get("exit_code", 0) == 0:
                return f"Database backed up successfully to: {output_path}"
            else:
                return f"Backup failed: {result.get('stderr', 'Unknown error')}"

        except Exception as e:
            return f"Error backing up database: {str(e)}"
