<?php

namespace Agtsdbx\Core\Middleware;

use Agtsdbx\Utils\Config;

class SecurityMiddleware
{
    private Config $config;
    
    public function __construct(Config $config)
    {
        $this->config = $config;
    }
    
    public function handle(array $request): array
    {
        // Add security headers
        header('X-Content-Type-Options: nosniff');
        header('X-Frame-Options: DENY');
        header('X-XSS-Protection: 1; mode=block');
        header('Referrer-Policy: no-referrer');
        
        // CORS headers if needed
        $allowedOrigins = $this->config->get('security.allowed_origins', []);
        $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
        
        if (in_array($origin, $allowedOrigins) || in_array('*', $allowedOrigins)) {
            header("Access-Control-Allow-Origin: $origin");
            header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
            header('Access-Control-Allow-Headers: Content-Type, Authorization');
        }
        
        // Handle preflight requests
        if ($request['method'] === 'OPTIONS') {
            http_response_code(204);
            exit;
        }
        
        return $request;
    }
}