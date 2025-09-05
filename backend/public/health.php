<?php
// ==============================================
// HEALTH CHECK ENDPOINT
// ==============================================

// Don't require autoloader for health check to minimize dependencies
header('Content-Type: application/json');

try {
    $health = [
        'status' => 'healthy',
        'timestamp' => date('c'),
        'version' => $_ENV['APP_VERSION'] ?? '1.0.0',
        'checks' => []
    ];
    
    // Check filesystem
    $workdir = $_ENV['WORKDIR'] ?? '/app/WORKDIR';
    $health['checks']['filesystem'] = is_dir($workdir) && is_writable($workdir);
    
    // Check PHP version
    $health['checks']['php'] = version_compare(PHP_VERSION, '8.0.0', '>=');
    
    // Check if vendor directory exists (basic check for dependencies)
    $health['checks']['dependencies'] = file_exists(dirname(__DIR__) . '/vendor/autoload.php');
    
    // Try Redis connection but don't fail health check if it's not ready
    if (extension_loaded('redis')) {
        try {
            $redis = new Redis();
            $redis_host = $_ENV['REDIS_HOST'] ?? 'redis';
            $redis_port = $_ENV['REDIS_PORT'] ?? 6379;
            
            // Short timeout for health check
            if (@$redis->connect($redis_host, $redis_port, 1.0)) {
                $health['checks']['redis'] = true;
                $redis->close();
            } else {
                $health['checks']['redis'] = false;
                error_log("Redis connection failed: Connection refused");
            }
        } catch (Exception $e) {
            $health['checks']['redis'] = false;
            error_log("Redis connection failed: " . $e->getMessage());
        }
    } else {
        $health['checks']['redis'] = null; // Redis extension not loaded
    }
    
    // Determine overall status
    // Don't fail on Redis - it's not critical for basic operation
    $critical_checks = ['filesystem', 'php', 'dependencies'];
    $allHealthy = true;
    
    foreach ($critical_checks as $check) {
        if (isset($health['checks'][$check]) && !$health['checks'][$check]) {
            $allHealthy = false;
            break;
        }
    }
    
    $health['status'] = $allHealthy ? 'healthy' : 'unhealthy';
    
    http_response_code($allHealthy ? 200 : 503);
    echo json_encode($health);
    
} catch (Throwable $e) {
    http_response_code(503);
    echo json_encode([
        'status' => 'unhealthy',
        'error' => $e->getMessage(),
        'timestamp' => date('c')
    ]);
}