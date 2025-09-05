<?php
// ==============================================
// HEALTH CHECK ENDPOINT - SIMPLIFIED VERSION
// ==============================================

// Simple health check that doesn't depend on autoloader or Redis
header('Content-Type: application/json');

try {
    $health = [
        'status' => 'healthy',
        'timestamp' => date('c'),
        'version' => $_ENV['APP_VERSION'] ?? '1.0.0',
        'checks' => []
    ];
    
    // Basic PHP check
    $health['checks']['php'] = version_compare(PHP_VERSION, '8.0.0', '>=');
    
    // Check if vendor exists (but don't load it)
    $health['checks']['vendor'] = file_exists(dirname(__DIR__) . '/vendor/autoload.php');
    
    // Check if workdir exists
    $workdir = $_ENV['WORKDIR'] ?? '/app/WORKDIR';
    $health['checks']['workdir'] = is_dir($workdir);
    
    // Simple overall status - only check critical items
    $health['status'] = ($health['checks']['php'] && $health['checks']['vendor']) ? 'healthy' : 'unhealthy';
    
    http_response_code($health['status'] === 'healthy' ? 200 : 503);
    echo json_encode($health);
    
} catch (Exception $e) {
    http_response_code(503);
    echo json_encode([
        'status' => 'unhealthy',
        'error' => $e->getMessage(),
        'timestamp' => date('c')
    ]);
}