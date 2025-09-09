# Magic Agent Sandbox - Complete System Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Deep Dive](#architecture-deep-dive)
3. [Data Flow Explained](#data-flow-explained)
4. [Component Interactions](#component-interactions)
5. [Setup & Configuration Guide](#setup--configuration-guide)
6. [Feature Implementations](#feature-implementations)
7. [Security Architecture](#security-architecture)
8. [Troubleshooting & Recommendations](#troubleshooting--recommendations)

---

## System Overview

Magic Agent Sandbox is a sophisticated AI-powered system management platform that bridges natural language interactions with system operations. Think of it as having an intelligent assistant that can understand your requests in plain English and execute complex system tasks safely and securely.

The system consists of three main layers working together:

**Layer 1: Intelligence Layer (Fabric/Tela AI)**
This is the brain of the system. When you type "Show me what files are in the current directory", the AI understands your intent and decides which tools to use.

**Layer 2: Orchestration Layer (Python Frontend)**
This middle layer acts as a translator and coordinator. It takes the AI's decisions and converts them into specific tool calls, managing the flow of information between the AI and the execution environment.

**Layer 3: Execution Layer (PHP Backend)**
This is where actual system operations happen. It provides a secure, sandboxed environment for running commands, managing files, and interacting with Docker containers.

## Architecture Deep Dive

### Frontend Architecture (Python/NiceGUI)

The frontend is built using Python with the NiceGUI framework, creating a responsive web interface. Let me walk you through how it's organized:

**Entry Point: `frontend/src/app/main.py`**

When the application starts, it follows this initialization sequence:

```python
# Step 1: Configuration Loading
config = Config()  # Loads from environment variables and config files

# Step 2: Authentication Setup
auth_manager = AuthManager(config)  # Manages user sessions and permissions

# Step 3: AI Client Initialization
fabric_client = FabricClient(fabric_config)  # Connects to Fabric/Tela AI

# Step 4: Backend Client Setup
agtsdbx_client = AgtsdbxClient(base_url)  # Connects to PHP backend

# Step 5: Tool Registration
tools = {
    "execution": ExecutionTools(agtsdbx_client),
    "file": FileTools(agtsdbx_client),
    "system": SystemTools(agtsdbx_client),
    "docker": DockerTools(agtsdbx_client),
    "network": NetworkTools(agtsdbx_client),
}
```

Each tool provides specific capabilities. For example, when you ask the AI to "create a Python script that calculates fibonacci numbers", here's what happens:

1. The AI receives your message
2. It decides to use the `file` tool to create a new file
3. The FileTools class generates the appropriate API call
4. The backend creates the actual file
5. The result flows back to you through the UI

### Backend Architecture (PHP)

The backend is structured as a RESTful API service with multiple layers of security and abstraction:

**Core Application Flow:**

```php
// Entry: backend/public/index.php
$app = new Application();
$app->run();

// The Application class (backend/src/Core/Application.php) then:
// 1. Initializes middleware stack
// 2. Registers routes
// 3. Processes requests through middleware
// 4. Routes to appropriate controller
// 5. Returns response
```

The middleware stack processes each request in order:

```
Request → SecurityMiddleware → LoggingMiddleware → AuthMiddleware 
        → RateLimitMiddleware → ValidationMiddleware → Controller
```

This layered approach ensures that every request is:
- Checked for security threats
- Logged for audit purposes
- Authenticated and authorized
- Rate-limited to prevent abuse
- Validated for correct format

## Data Flow Explained

Let me trace a complete request through the system with a real example:

### Example: "List all Python files in the current directory"

**Step 1: User Input**
You type this request in the chat interface (`frontend/src/ui/components/chat.py`).

**Step 2: Message Processing**
```python
# In AgtsdbxApp.send_message()
user_message = "List all Python files in the current directory"
messages.append({"role": "user", "content": user_message})
```

**Step 3: AI Analysis**
The Fabric AI receives the message with available tool definitions:
```python
response = await fabric_client.chat_completion(
    messages=messages,
    tools=get_all_tool_definitions(),  # Includes file listing tool
    tool_choice="auto"
)
```

**Step 4: Tool Selection**
The AI responds with a tool call:
```json
{
    "tool_calls": [{
        "function": {
            "name": "list_files",
            "arguments": "{\"path\": \".\", \"pattern\": \"*.py\"}"
        }
    }]
}
```

**Step 5: Tool Execution**
The FileTools class processes this:
```python
async def list_files(self, path=".", pattern="*"):
    async with self.agtsdbx_client as client:
        result = await client.list_files(path, {"pattern": pattern})
```

**Step 6: Backend Processing**
The PHP backend receives the request at `/api/v1/file/list`:
```php
// FileController::list()
$files = $this->fileService->list($path, $options);
// Security checks ensure path is allowed
// Returns filtered list of .py files
```

**Step 7: Response Flow**
The file list travels back:
```
Backend → AgtsdbxClient → FileTools → AI → Chat UI → You
```

You see a formatted response like:
```
Found 5 Python files:
- main.py
- config.py
- utils.py
- test_app.py
- setup.py
```

## Component Interactions

### WebSocket Real-time Updates

The system maintains a WebSocket connection for real-time updates. When you execute a long-running command, you see live output:

```javascript
// frontend/static/js/app.js
wsConnection.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'command_output') {
        displayCommandOutput(message.data);  // Shows output as it happens
    }
}
```

### Docker Integration

When you request "Run a Python container and execute a script", the system:

1. **Validates the request** through SecurityManager
2. **Checks allowed images** (python:3.11-slim is whitelisted)
3. **Applies resource limits**:
   ```php
   $dockerCommand .= ' --memory=512m';  // Memory limit
   $dockerCommand .= ' --cpus=0.5';     // CPU limit
   $dockerCommand .= ' --network=none'; // Network isolation
   ```
4. **Executes safely** in isolated environment
5. **Returns output** through the same secure pipeline

### Database Operations

The system supports SQLite, PostgreSQL, and MySQL operations:

```python
# When you ask: "Show me all users in the database"
async def execute_sql(database_type="postgresql", query="SELECT * FROM users"):
    # The system ensures it's a SELECT query (read-only)
    # Connects using configured credentials
    # Returns formatted results
```

## Setup & Configuration Guide

### Essential Configuration

The system REQUIRES three Fabric/Tela credentials in your `.env` file:

```bash
# MANDATORY - Without these, AI integration won't work
FABRIC_API_KEY=your_actual_api_key_here
FABRIC_ORG_ID=your_organization_id_here  
FABRIC_PROJECT_ID=your_project_id_here

# The system validates these on startup:
def validate_config(self):
    required = ['FABRIC_API_KEY', 'FABRIC_ORG_ID', 'FABRIC_PROJECT_ID']
    missing = [key for key in required if not self.config.get(key)]
    if missing:
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")
```

### Step-by-Step Setup

1. **Clone and prepare the environment:**
   ```bash
   git clone <repository>
   cd agent-sandbox
   
   # Run the setup script
   ./setup.sh
   ```

2. **Configure your credentials:**
   ```bash
   # Edit .env file
   nano .env
   
   # Add your Fabric credentials (obtained from Tela platform)
   FABRIC_API_KEY=fab_sk_xxxxxxxxxxxx
   FABRIC_ORG_ID=org_xxxxxxxxxxxx
   FABRIC_PROJECT_ID=proj_xxxxxxxxxxxx
   ```

3. **Start the development environment:**
   ```bash
   make dev
   
   # This starts:
   # - PostgreSQL database on port 15432
   # - Redis cache on port 16379
   # - PHP backend on port 8000
   # - Python frontend on port 8080
   ```

4. **Access the application:**
   Open your browser to `http://localhost:8080`

## Feature Implementations

### Command Execution with Timeout

When you request command execution, the system implements multiple safety layers:

```python
# Frontend tool definition
async def execute_shell_command(command, timeout=300):
    # First layer: Client-side validation
    
    # Second layer: Backend security
    # The PHP backend checks against blacklist:
    $blacklist = ['rm -rf /', 'mkfs', 'shutdown', 'reboot'];
    
    # Third layer: Sandboxing
    # Commands run in isolated environment with:
    # - Limited filesystem access
    # - No network access (unless explicitly allowed)
    # - Resource limits (CPU, memory, time)
    
    # Fourth layer: Timeout enforcement
    $fullCommand = sprintf('timeout %d bash -c %s', $timeout, $command);
```

### File Operations with Path Security

The file system access is strictly controlled:

```php
// backend/src/Core/Security/SecurityManager.php
public function isPathAllowed(string $path): bool {
    // Only these paths are accessible:
    $allowed_paths = [
        '/app/WORKDIR',     // Primary workspace
        '/tmp/agtsdbx'      // Temporary files
    ];
    
    // These are always blocked:
    $forbidden_paths = [
        '/etc',    // System configuration
        '/root',   // Root user directory
        '/var',    // System variables
        '..',      // Parent directory traversal
    ];
}
```

### System Monitoring

The monitoring system continuously tracks system health:

```python
# Frontend monitoring component
async def refresh_data(self):
    system_info = await system_tools.get_system_info()
    # Updates CPU, Memory, Disk usage displays
    
    # The backend provides real metrics:
    # - CPU usage via /proc/stat
    # - Memory via /proc/meminfo  
    # - Disk usage via df command
    # - Network status via netstat/ss
```

## Security Architecture

### Multi-Layer Security Model

The system implements defense in depth:

**Layer 1: Input Validation**
```python
# All user input is validated
if len(command) > MAX_COMMAND_LENGTH:
    raise ValueError("Command too long")
```

**Layer 2: Authentication & Authorization**
```python
# JWT tokens with expiration
token = jwt.encode({
    "user_id": user_id,
    "role": role,
    "exp": datetime.utcnow() + timedelta(hours=1)
}, secret_key)
```

**Layer 3: Command Filtering**
```php
// Dangerous patterns are blocked
$dangerousPatterns = [
    '/\|\s*sh\s*$/',      // Pipe to shell
    '/\$\(.*\)/',         // Command substitution
    '/`.*`/',             // Backtick execution
];
```

**Layer 4: Sandboxing**
```php
// Commands run with restrictions
if ($this->hasFirejail()) {
    $command = "firejail --noprofile --noroot --caps.drop=all " . $command;
}
```

**Layer 5: Resource Limits**
```php
// Prevent resource exhaustion
$limits = [
    'ulimit -t 300',     // CPU time limit
    'ulimit -v 524288',  // Memory limit (512MB)
    'ulimit -f 102400',  // File size limit (100MB)
];
```

## Troubleshooting & Recommendations

### Current Issues and Solutions

**Issue 1: WebSocket Reconnection**
The current implementation has a basic reconnection strategy. I recommend enhancing it:

```javascript
// Improved reconnection with exponential backoff
class WebSocketManager {
    constructor() {
        this.reconnectDelay = 1000;
        this.maxDelay = 30000;
        this.reconnectAttempts = 0;
    }
    
    reconnect() {
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
            this.maxDelay
        );
        setTimeout(() => this.connect(), delay);
        this.reconnectAttempts++;
    }
}
```

**Issue 2: Memory Management in Tool Execution**
The current parallel execution could consume excessive memory. Consider implementing a worker pool:

```python
# Better approach using asyncio.Semaphore
class ExecutionPool:
    def __init__(self, max_workers=5):
        self.semaphore = asyncio.Semaphore(max_workers)
        self.active_tasks = []
    
    async def execute(self, command):
        async with self.semaphore:
            # Ensures only max_workers run simultaneously
            return await self._run_command(command)
```

**Issue 3: Database Connection Pooling**
The PHP backend creates new connections for each request. Implement connection pooling:

```php
class DatabasePool {
    private static $connections = [];
    private static $maxConnections = 10;
    
    public static function getConnection($database) {
        if (!isset(self::$connections[$database])) {
            if (count(self::$connections) >= self::$maxConnections) {
                // Reuse least recently used connection
                self::closeLRUConnection();
            }
            self::$connections[$database] = self::createConnection($database);
        }
        return self::$connections[$database];
    }
}
```

### Recommended Improvements for 2025

1. **Implement OpenTelemetry for observability:**
   ```python
   from opentelemetry import trace
   tracer = trace.get_tracer(__name__)
   
   @tracer.start_as_current_span("execute_command")
   async def execute_command(self, command):
       # Automatic tracing of all operations
   ```

2. **Add GraphQL API alongside REST:**
   ```python
   # More efficient data fetching
   query = """
   query SystemStatus {
       system {
           cpu { usage cores }
           memory { used total }
           disk { used total }
       }
   }
   """
   ```

3. **Implement Circuit Breaker pattern:**
   ```python
   from pybreaker import CircuitBreaker
   
   backend_breaker = CircuitBreaker(
       fail_max=5,
       reset_timeout=60,
       expected_exception=ConnectionError
   )
   
   @backend_breaker
   async def call_backend(self, endpoint):
       # Automatically stops calling failed services
   ```

4. **Add Kubernetes native deployment:**
   ```yaml
   # Use StatefulSets for backend
   # Use Horizontal Pod Autoscaler for frontend
   # Implement proper health probes
   ```

### Performance Optimizations

1. **Cache AI responses for similar queries:**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   async def get_cached_ai_response(query_hash):
       # Cache frequently asked questions
   ```

2. **Implement request debouncing in UI:**
   ```javascript
   function debounce(func, wait) {
       let timeout;
       return function executedFunction(...args) {
           const later = () => {
               clearTimeout(timeout);
               func(...args);
           };
           clearTimeout(timeout);
           timeout = setTimeout(later, wait);
       };
   }
   ```

## Complete Usage Examples

### Example 1: Deploy a Web Application

```python
User: "Deploy a simple Python web app with Flask"

# System responds by:
# 1. Creating app.py file
await file_tools.write_file("app.py", '''
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Agent Sandbox!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
''')

# 2. Creating requirements.txt
await file_tools.write_file("requirements.txt", "flask==2.3.0")

# 3. Creating Dockerfile
await file_tools.write_file("Dockerfile", '''
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
''')

# 4. Building and running container
await docker_tools.docker_run(
    image="my-flask-app",
    ports={"5000": "5000"}
)
```

### Example 2: System Health Check

```python
User: "Check system health and create a report"

# System performs:
system_info = await system_tools.get_system_info()
process_list = await system_tools.get_process_list(sort_by="memory")
disk_usage = await system_tools.check_disk_usage()
network_status = await system_tools.check_network_connectivity()

# Generates formatted report
report = f"""
System Health Report - {datetime.now()}
=====================================
CPU Usage: {system_info['cpu']['usage']}%
Memory: {system_info['memory']['used']}/{system_info['memory']['total']}
Disk: {disk_usage}
Network: {network_status}

Top Processes by Memory:
{process_list}
"""

await file_tools.write_file("health_report.md", report)
```

### Example 3: Database Backup Automation

```python
User: "Backup all databases and compress them"

# System executes:
# 1. List databases
databases = await db_tools.execute_sql(
    "SELECT datname FROM pg_database WHERE datistemplate = false"
)

# 2. Backup each database
for db in databases:
    await execution_tools.execute_shell_command(
        f"pg_dump {db} > /app/WORKDIR/{db}_backup.sql"
    )

# 3. Compress backups
await execution_tools.execute_shell_command(
    "tar -czf backups_$(date +%Y%m%d).tar.gz *.sql"
)

# 4. Clean up individual files
await execution_tools.execute_shell_command("rm *.sql")
```

## System Maintenance

### Daily Operations

Monitor the system health through Grafana dashboards at `http://localhost:3000`. Key metrics to watch:

- **Request latency**: Should stay under 500ms for simple operations
- **Error rate**: Should remain below 1%
- **CPU usage**: Backend should stay under 70%
- **Memory usage**: Frontend should not exceed 512MB per instance

### Backup Strategy

The system includes automated backup capabilities:

```bash
# Manual backup
./scripts/backup.sh

# Automated daily backup (add to crontab)
0 2 * * * /path/to/agent-sandbox/scripts/backup.sh
```

### Log Management

Logs are stored in structured format:
- Backend logs: `backend/storage/logs/app.log`
- Frontend logs: Sent to stdout (captured by Docker)
- System logs: Available via `docker-compose logs`

## Conclusion

The Magic Agent Sandbox represents a sophisticated integration of AI capabilities with system management tools. The architecture ensures security through multiple layers of protection while maintaining flexibility and extensibility. The clear separation between the intelligence layer (AI), orchestration layer (Frontend), and execution layer (Backend) allows for independent scaling and maintenance of each component.

The system is production-ready with proper error handling, logging, and monitoring in place. However, the recommended improvements would enhance its reliability and performance for high-scale deployments. The modular design allows for easy addition of new tools and capabilities as requirements evolve.