<?php

namespace Agtsdbx\Core\Middleware;

use Agtsdbx\Utils\Logger;
use Agtsdbx\Utils\Config;

class LoggingMiddleware
{
    private Logger $logger;
    
    public function __construct(Logger $logger)
    {
        $this->logger = $logger;
    }
    
    public function handle(array $request): array
    {
        // Log request
        $this->logger->info('Incoming request', [
            'method' => $request['method'],
            'uri' => $request['uri'],
            'ip' => $request['ip'],
            'user_agent' => $request['user_agent']
        ]);
        
        // Add request ID
        $request['request_id'] = uniqid('req_', true);
        
        return $request;
    }
}