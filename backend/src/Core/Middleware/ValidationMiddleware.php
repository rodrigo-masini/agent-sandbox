<?php

namespace Agtsdbx\Core\Middleware;

use Agtsdbx\Utils\Config;

class ValidationMiddleware
{
    private Config $config;
    
    public function __construct(Config $config)
    {
        $this->config = $config;
    }
    
    public function handle(array $request): array
    {
        // Validate request size
        $maxSize = $this->config->get('network.max_request_size', 1048576);
        $contentLength = $_SERVER['CONTENT_LENGTH'] ?? 0;
        
        if ($contentLength > $maxSize) {
            throw new \Exception('Request too large', 413);
        }
        
        // Validate content type for POST/PUT requests
        if (in_array($request['method'], ['POST', 'PUT', 'PATCH'])) {
            $contentType = $request['headers']['Content-Type'] ?? '';
            if (!str_contains($contentType, 'application/json')) {
                throw new \Exception('Content-Type must be application/json', 400);
            }
        }
        
        return $request;
    }
}