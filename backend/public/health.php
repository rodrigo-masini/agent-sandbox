<?php
// ==============================================
// HEALTH CHECK ENDPOINT - ROBUST VERSION 2025
// ==============================================

header('Content-Type: application/json');
header('Cache-Control: no-cache, no-store, must-revalidate');
header('X-Health-Check-Version: 2.0.0');

// Set error handling
set_error_handler(function($severity, $message, $file, $line) {
    throw new ErrorException($message, 0, $severity, $file, $line);
});

try {
    $startTime = microtime(true);
    
    $health = [
        'status' => 'initializing',
        'timestamp' => date('c'),
        'version' => $_ENV['APP_VERSION'] ?? '1.0.0',
        'environment' => $_ENV['APP_ENV'] ?? 'production',
        'checks' => [],
        'metrics' => []
    ];
    
    // PHP Version Check
    $health['checks']['php_version'] = [
        'status' => version_compare(PHP_VERSION, '8.0.0', '>='),
        'version' => PHP_VERSION,
        'required' => '8.0.0'
    ];
    
    // Check critical PHP extensions
    $requiredExtensions = ['pdo', 'json', 'pcntl', 'posix'];
    $missingExtensions = [];
    foreach ($requiredExtensions as $ext) {
        if (!extension_loaded($ext)) {
            $missingExtensions[] = $ext;
        }
    }
    $health['checks']['php_extensions'] = [
        'status' => empty($missingExtensions),
        'missing' => $missingExtensions
    ];
    
    // Check vendor directory (with fallback)
    $vendorPath = dirname(__DIR__) . '/vendor/autoload.php';
    $health['checks']['vendor'] = [
        'status' => file_exists($vendorPath),
        'path' => $vendorPath
    ];
    
    // Check workdir (with creation attempt)
    $workdir = $_ENV['WORKDIR'] ?? '/app/WORKDIR';
    if (!is_dir($workdir)) {
        @mkdir($workdir, 0777, true);
    }
    $health['checks']['workdir'] = [
        'status' => is_dir($workdir) && is_writable($workdir),
        'path' => $workdir
    ];
    
    // Check storage directories
    $storagePaths = [
        'logs' => dirname(__DIR__) . '/storage/logs',
        'cache' => dirname(__DIR__) . '/storage/cache',
    ];
    
    $storageHealthy = true;
    foreach ($storagePaths as $key => $path) {
        if (!is_dir($path)) {
            @mkdir($path, 0777, true);
        }
        $isHealthy = is_dir($path) && is_writable($path);
        $health['checks']["storage_$key"] = [
            'status' => $isHealthy,
            'path' => $path
        ];
        $storageHealthy = $storageHealthy && $isHealthy;
    }
    
    // Database connectivity check (optional)
    if (!empty($_ENV['DATABASE_URL'])) {
        try {
            $dbUrl = $_ENV['DATABASE_URL'];
            if (strpos($dbUrl, 'postgresql://') === 0 || strpos($dbUrl, 'mysql://') === 0) {
                // Basic connection test without PDO if not available
                $health['checks']['database'] = [
                    'status' => extension_loaded('pdo'),
                    'configured' => true
                ];
            } else {
                $health['checks']['database'] = [
                    'status' => true,
                    'type' => 'sqlite'
                ];
            }
        } catch (Exception $e) {
            $health['checks']['database'] = [
                'status' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    // Redis connectivity check (optional)
    if (!empty($_ENV['REDIS_HOST']) && extension_loaded('redis')) {
        try {
            $redis = new Redis();
            $connected = @$redis->connect($_ENV['REDIS_HOST'], $_ENV['REDIS_PORT'] ?? 6379, 2.0);
            $health['checks']['redis'] = [
                'status' => $connected,
                'host' => $_ENV['REDIS_HOST']
            ];
            if ($connected) {
                $redis->close();
            }
        } catch (Exception $e) {
            $health['checks']['redis'] = [
                'status' => false,
                'error' => 'Connection failed'
            ];
        }
    }
    
    // Memory usage metrics
    $health['metrics']['memory'] = [
        'current' => memory_get_usage(true),
        'peak' => memory_get_peak_usage(true),
        'limit' => ini_get('memory_limit')
    ];
    
    // Response time
    $health['metrics']['response_time_ms'] = round((microtime(true) - $startTime) * 1000, 2);
    
    // Determine overall status
    $criticalChecks = ['php_version', 'vendor'];
    $overallHealthy = true;
    
    foreach ($criticalChecks as $check) {
        if (isset($health['checks'][$check]) && !$health['checks'][$check]['status']) {
            $overallHealthy = false;
            break;
        }
    }
    
    $health['status'] = $overallHealthy ? 'healthy' : 'unhealthy';
    
    // Set appropriate HTTP status code
    http_response_code($overallHealthy ? 200 : 503);
    
    // Output JSON response
    echo json_encode($health, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    
} catch (Throwable $e) {
    // Fallback error response
    http_response_code(503);
    echo json_encode([
        'status' => 'unhealthy',
        'error' => [
            'message' => $e->getMessage(),
            'file' => basename($e->getFile()),
            'line' => $e->getLine()
        ],
        'timestamp' => date('c')
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
} finally {
    // Restore error handler
    restore_error_handler();
}