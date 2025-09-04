<?php
// ==============================================
// MAIN ENTRY POINT
// ==============================================

require_once dirname(__DIR__) . '/vendor/autoload.php';

use Pandora\Core\Application;

// Enable error reporting in development
if (($_ENV['APP_ENV'] ?? 'development') === 'development') {
    error_reporting(E_ALL);
    ini_set('display_errors', 1);
} else {
    error_reporting(0);
    ini_set('display_errors', 0);
}

// Set timezone
date_default_timezone_set($_ENV['TIMEZONE'] ?? 'UTC');

// Create and run application
try {
    $app = new Application();
    $app->run();
} catch (\Throwable $e) {
    http_response_code(500);
    header('Content-Type: application/json');
    
    $response = [
        'error' => 'Internal server error',
        'timestamp' => date('c')
    ];
    
    if (($_ENV['APP_DEBUG'] ?? 'false') === 'true') {
        $response['message'] = $e->getMessage();
        $response['file'] = $e->getFile();
        $response['line'] = $e->getLine();
    }
    
    echo json_encode($response);
}
