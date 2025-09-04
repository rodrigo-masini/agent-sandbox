// Agent Sandbox Frontend JavaScript
class AgentSandbox {
    constructor() {
        this.wsConnection = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.init();
    }

    init() {
        this.setupWebSocket();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.checkSystemStatus();
    }

    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        try {
            this.wsConnection = new WebSocket(wsUrl);
            
            this.wsConnection.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
            };

            this.wsConnection.onmessage = (event) => {
                this.handleWebSocketMessage(event.data);
            };

            this.wsConnection.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus('error');
            };

            this.wsConnection.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus('disconnected');
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Failed to setup WebSocket:', error);
        }
    }

    handleWebSocketMessage(data) {
        try {
            const message = JSON.parse(data);
            
            switch (message.type) {
                case 'command_output':
                    this.displayCommandOutput(message.data);
                    break;
                case 'file_update':
                    this.refreshFileList(message.data);
                    break;
                case 'system_metrics':
                    this.updateSystemMetrics(message.data);
                    break;
                case 'notification':
                    this.showNotification(message.data);
                    break;
                default:
                    console.log('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Reconnection attempt ${this.reconnectAttempts}`);
                this.setupWebSocket();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            this.showNotification({
                type: 'error',
                message: 'Failed to reconnect to server. Please refresh the page.'
            });
        }
    }

    sendWebSocketMessage(type, data) {
        if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
            this.wsConnection.send(JSON.stringify({ type, data }));
        } else {
            console.error('WebSocket is not connected');
            this.showNotification({
                type: 'warning',
                message: 'Connection lost. Attempting to reconnect...'
            });
        }
    }

    setupEventListeners() {
        // Terminal input handler
        const terminalInput = document.getElementById('terminal-input');
        if (terminalInput) {
            terminalInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.executeCommand(terminalInput.value);
                    terminalInput.value = '';
                }
            });
        }

        // File upload handler
        const fileUpload = document.getElementById('file-upload');
        if (fileUpload) {
            fileUpload.addEventListener('change', (e) => {
                this.handleFileUpload(e.target.files);
            });
        }

        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K: Focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.getElementById('search-input');
                if (searchInput) searchInput.focus();
            }

            // Ctrl/Cmd + Enter: Execute command
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                const activeElement = document.activeElement;
                if (activeElement && activeElement.classList.contains('command-input')) {
                    this.executeCommand(activeElement.value);
                }
            }

            // Escape: Close modal
            if (e.key === 'Escape') {
                this.closeActiveModal();
            }
        });
    }

    async checkSystemStatus() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            this.updateSystemStatus(data);
        } catch (error) {
            console.error('Failed to check system status:', error);
            this.updateSystemStatus({ status: 'error' });
        }

        // Check again in 30 seconds
        setTimeout(() => this.checkSystemStatus(), 30000);
    }

    updateSystemStatus(status) {
        const statusElements = {
            fabric: document.getElementById('fabric-status'),
            agtsdbx: document.getElementById('agtsdbx-status'),
            docker: document.getElementById('docker-status')
        };

        Object.keys(statusElements).forEach(service => {
            const element = statusElements[service];
            if (element && status.services && status.services[service]) {
                const serviceStatus = status.services[service].status;
                element.className = `status-indicator ${serviceStatus}`;
                element.title = `${service}: ${serviceStatus}`;
            }
        });
    }

    async executeCommand(command) {
        if (!command.trim()) return;

        this.sendWebSocketMessage('execute_command', { command });
        
        // Add command to history
        this.addToCommandHistory(command);
    }

    addToCommandHistory(command) {
        const history = JSON.parse(localStorage.getItem('commandHistory') || '[]');
        history.push({
            command,
            timestamp: new Date().toISOString()
        });
        
        // Keep only last 100 commands
        if (history.length > 100) {
            history.shift();
        }
        
        localStorage.setItem('commandHistory', JSON.stringify(history));
    }

    displayCommandOutput(data) {
        const outputContainer = document.getElementById('terminal-output');
        if (!outputContainer) return;

        const outputElement = document.createElement('div');
        outputElement.className = 'terminal-output-item';
        
        if (data.error) {
            outputElement.classList.add('error');
            outputElement.textContent = `Error: ${data.error}`;
        } else {
            outputElement.innerHTML = this.formatOutput(data.output);
        }
        
        outputContainer.appendChild(outputElement);
        outputContainer.scrollTop = outputContainer.scrollHeight;
    }

    formatOutput(output) {
        // Basic ANSI color support
        const ansiColors = {
            '30': 'black',
            '31': 'red',
            '32': 'green',
            '33': 'yellow',
            '34': 'blue',
            '35': 'magenta',
            '36': 'cyan',
            '37': 'white'
        };

        return output.replace(/\033\[(\d+)m/g, (match, code) => {
            const color = ansiColors[code];
            return color ? `<span style="color: ${color}">` : '</span>';
        });
    }

    async handleFileUpload(files) {
        const formData = new FormData();
        
        for (const file of files) {
            formData.append('files', file);
        }

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification({
                    type: 'success',
                    message: `Successfully uploaded ${files.length} file(s)`
                });
                this.refreshFileList();
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            this.showNotification({
                type: 'error',
                message: `Upload failed: ${error.message}`
            });
        }
    }

    refreshFileList(path = '.') {
        this.sendWebSocketMessage('list_files', { path });
    }

    updateSystemMetrics(metrics) {
        const elements = {
            'cpu-usage': metrics.cpu,
            'memory-usage': metrics.memory,
            'disk-usage': metrics.disk,
            'network-status': metrics.network
        };

        Object.keys(elements).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = elements[id];
            }
        });
    }

    showNotification(data) {
        const notification = document.createElement('div');
        notification.className = `notification ${data.type}`;
        notification.textContent = data.message;
        
        const container = document.getElementById('notification-container') || document.body;
        container.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    toggleTheme() {
        const currentTheme = localStorage.getItem('theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.body.className = `theme-${newTheme}`;
        localStorage.setItem('theme', newTheme);
    }

    updateConnectionStatus(status) {
        const indicator = document.getElementById('connection-status');
        if (indicator) {
            indicator.className = `status-indicator ${status}`;
            indicator.title = `WebSocket: ${status}`;
        }
    }

    closeActiveModal() {
        const modal = document.querySelector('.modal.active');
        if (modal) {
            modal.classList.remove('active');
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.agentSandbox = new AgentSandbox();
});