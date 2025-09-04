<?php
// ==============================================
// HEALTH CHECK ENDPOINT
// ==============================================

require_once dirname(__DIR__) . '/vendor/autoload.php';

use Agtsdbx\Core\Application;

header('Content-Type: application/json');

try {
    // Don't initialize full application for health check
    // Just check basic requirements
    
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
    
    // Check composer autoload
    $health['checks']['autoload'] = class_exists('Agtsdbx\Utils\Config');
    
    // Overall status
    $allHealthy = true;
    foreach ($health['checks'] as $check) {
        if (!$check) {
            $allHealthy = false;
            break;
        }
    }
    
    $health['status'] = $allHealthy ? 'healthy' : 'unhealthy';
    
    http_response_code($allHealthy ? 200 : 503);
    echo json_encode($health);
    
} catch (\Throwable $e) {
    http_response_code(503);
    echo json_encode([
        'status' => 'unhealthy',
        'error' => $e->getMessage(),
        'timestamp' => date('c')
    ]);
}
