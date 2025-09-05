<?php

// Helper function to read environment variables with type casting
function get_env(string $key, $default = null) {
    $value = $_ENV[$key] ?? $default;
    if (is_bool($default)) {
        return filter_var($value, FILTER_VALIDATE_BOOLEAN);
    }
    if (is_int($default)) {
        return (int) $value;
    }
    return $value;
}

return [
    // Authentication settings
    'auth' => [
        'jwt_secret' => $_ENV['JWT_SECRET'] ?? '',
        'jwt_expiry' => $_ENV['JWT_EXPIRY'] ?? 3600,
        'api_keys' => explode(',', $_ENV['API_KEYS'] ?? ''),
        'require_auth' => ($_ENV['REQUIRE_AUTH'] ?? 'true') === 'true',
    ],
    
    // Rate limiting
    'rate_limit' => [
        'enabled' => ($_ENV['RATE_LIMIT_ENABLED'] ?? 'true') === 'true',
        'requests_per_minute' => (int)($_ENV['RATE_LIMIT_RPM'] ?? 60),
        'window_seconds' => (int)($_ENV['RATE_LIMIT_WINDOW'] ?? 60),
        'burst_limit' => (int)($_ENV['RATE_LIMIT_BURST'] ?? 100),
    ],

    // Command security
    'commands' => [
        'whitelist_enabled' => get_env('COMMAND_WHITELIST_ENABLED', false),
        'blacklist_enabled' => get_env('COMMAND_BLACKLIST_ENABLED', true),
        'whitelist' => [
            'ls', 'cat', 'echo', 'pwd', 'whoami', 'date', 'uptime',
            'ps', 'top', 'df', 'du', 'free', 'uname',
            'python', 'python3', 'node', 'npm', 'git',
            'docker', 'kubectl', 'curl', 'wget'
        ],
        'blacklist' => [
            'rm -rf /', 'dd if=', 'mkfs', 'fdisk', 'parted',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'passwd', 'su', 'sudo', 'chmod 777',
            'iptables', 'ufw', 'firewall-cmd',
            'crontab', 'at', 'batch',
            'nc -l', 'netcat -l', 'socat',
            '> /dev/', '< /dev/', '| dd', '| tee /dev/'
        ],
        'max_length' => get_env('COMMAND_MAX_LENGTH', 1000),
        'timeout' => get_env('COMMAND_TIMEOUT', 300),
    ],

    // File system security
    'filesystem' => [
        'allowed_paths' => [
            '/app/WORKDIR',
            '/tmp/agtsdbx', // Standardized name
        ],
        'forbidden_paths' => [
            '/', '/etc', '/usr', '/var', '/bin', '/sbin',
            '/boot', '/dev', '/proc', '/sys', '/root',
            '/home', '..', '../'
        ],
        'max_file_size' => get_env('MAX_FILE_SIZE', 10485760), // 10MB
        'allowed_extensions' => [
            'txt', 'md', 'json', 'yaml', 'yml', 'xml',
            'py', 'js', 'ts', 'php', 'java', 'c', 'cpp',
            'html', 'css', 'scss', 'less',
            'sh', 'bash', 'zsh', 'fish',
            'sql', 'csv', 'log'
        ],
    ],

    // Network security
    'network' => [
        'allowed_domains' => [
            'api.github.com',
            'registry.npmjs.org',
            'pypi.org',
            'packagist.org',
            'hub.docker.com',
        ],
        'blocked_ips' => [
            '127.0.0.1', 'localhost',
            '10.0.0.0/8',
            '172.16.0.0/12',
            '192.168.0.0/16',
        ],
        'max_request_size' => get_env('MAX_REQUEST_SIZE', 1048576), // 1MB
        'timeout' => get_env('NETWORK_TIMEOUT', 30),
    ],

    // Docker security
    'docker' => [
        'enabled' => get_env('DOCKER_ENABLED', true),
        'allowed_images' => [
            'python:3.11-slim',
            'node:18-alpine',
            'ubuntu:22.04',
            'alpine:latest',
            'nginx:alpine',
            'redis:7-alpine',
        ],
        'resource_limits' => [
            'memory' => '512m',
            'cpu' => '0.5',
            'disk' => '1g',
        ],
        'network_mode' => 'none', // No network access by default
        'read_only' => true,
        'no_new_privileges' => true,
    ],

    // Logging and monitoring
    'logging' => [
        'log_commands' => get_env('LOG_COMMANDS', true),
        'log_file_access' => get_env('LOG_FILE_ACCESS', true),
        'log_network_requests' => get_env('LOG_NETWORK_REQUESTS', true),
        'sensitive_patterns' => [
            '/password/i',
            '/secret/i',
            '/token/i',
            '/key/i',
            '/credential/i',
        ],
    ],

    // Encryption
    'encryption' => [
        'algorithm' => 'AES-256-GCM',
        'key' => get_env('ENCRYPTION_KEY'),
    ],
];