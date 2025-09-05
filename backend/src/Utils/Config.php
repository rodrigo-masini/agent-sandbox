<?php
// ==============================================
// CONFIG IMPLEMENTATION
// ==============================================

namespace Agtsdbx\Utils;

class Config
{
    private static ?Config $instance = null;
    private array $config = [];

    public function __construct(string $configPath = null)
    {
        $this->loadEnvironment();
        $this->loadConfigFiles($configPath);
    }

    // Add a static method to get the single instance
    public static function getInstance(string $configPath = null): Config
    {
        if (self::$instance === null) {
            self::$instance = new self($configPath);
        }
        return self::$instance;
    }

    // Prevent cloning and unserialization
    private function __clone() {}
    public function __wakeup() {}    

    private function loadEnvironment(): void
    {
        // Load from environment variables
        $this->config = [
            'app' => [
                'env' => $_ENV['APP_ENV'] ?? 'development',
                'debug' => ($_ENV['APP_DEBUG'] ?? 'false') === 'true',
                'name' => $_ENV['APP_NAME'] ?? 'Agtsdbx',
                'version' => $_ENV['APP_VERSION'] ?? '1.0.0'
            ],
            'workdir' => $_ENV['WORKDIR'] ?? '/app/WORKDIR',
            'logging' => [
                'level' => $_ENV['LOG_LEVEL'] ?? 'info',
                'path' => $_ENV['LOG_PATH'] ?? '/app/storage/logs/app.log'
            ],
            'auth' => [
                'jwt_secret' => $_ENV['JWT_SECRET'] ?? '',
                'jwt_expiry' => (int)($_ENV['JWT_EXPIRY'] ?? 3600),
                'api_keys' => explode(',', $_ENV['API_KEYS'] ?? ''),
                'require_auth' => ($_ENV['REQUIRE_AUTH'] ?? 'true') === 'true'
            ],
            'rate_limit' => [
                'enabled' => ($_ENV['RATE_LIMIT_ENABLED'] ?? 'true') === 'true',
                'requests_per_minute' => (int)($_ENV['RATE_LIMIT_RPM'] ?? 60),
                'window_seconds' => (int)($_ENV['RATE_LIMIT_WINDOW'] ?? 60)
            ],
            'sandbox' => [
                'enabled' => ($_ENV['SANDBOX_ENABLED'] ?? 'true') === 'true'
            ],
            'docker' => [
                'enabled' => ($_ENV['DOCKER_ENABLED'] ?? 'true') === 'true',
                'allowed_images' => explode(',', $_ENV['DOCKER_ALLOWED_IMAGES'] ?? ''),
                'resource_limits' => [
                    'memory' => $_ENV['DOCKER_MEMORY_LIMIT'] ?? '512m',
                    'cpu' => $_ENV['DOCKER_CPU_LIMIT'] ?? '0.5'
                ],
                'read_only' => ($_ENV['DOCKER_READ_ONLY'] ?? 'true') === 'true',
                'no_new_privileges' => true,
                'network_mode' => $_ENV['DOCKER_NETWORK_MODE'] ?? 'none'
            ]
        ];
    }

    private function loadConfigFiles(string $configPath = null): void
    {
        $configDir = $configPath ?? dirname(__DIR__, 2) . '/config';
        
        if (!is_dir($configDir)) {
            return;
        }

        $files = glob($configDir . '/*.php');
        
        foreach ($files as $file) {
            $key = basename($file, '.php');
            $fileConfig = include $file;
            
            if (is_array($fileConfig)) {
                $this->config[$key] = array_merge($this->config[$key] ?? [], $fileConfig);
            }
        }
    }

    public function get(string $key, mixed $default = null): mixed // ADD TYPES
    {
        $keys = explode('.', $key);
        $value = $this->config;

        foreach ($keys as $k) {
            if (!isset($value[$k])) {
                return $default;
            }
            $value = $value[$k];
        }

        return $value;
    }

    public function set(string $key, mixed $value): void // ADD TYPE
    {
        $keys = explode('.', $key);
        $config = &$this->config;

        foreach ($keys as $i => $k) {
            if ($i === count($keys) - 1) {
                $config[$k] = $value;
            } else {
                if (!isset($config[$k]) || !is_array($config[$k])) {
                    $config[$k] = [];
                }
                $config = &$config[$k];
            }
        }
    }

    public function all(): array
    {
        return $this->config;
    }
}
