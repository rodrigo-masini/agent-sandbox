<?php

namespace Pandora\Core\Middleware;

use Pandora\Utils\Config;
use Firebase\JWT\JWT;
use Firebase\JWT\Key;

class AuthMiddleware
{
    private Config $config;
    private array $publicEndpoints = ['/health', '/api/v1/system/info'];

    public function __construct(Config $config)
    {
        $this->config = $config;
    }

    public function handle(array $request): array
    {
        // Skip authentication for public endpoints
        if (in_array($request['uri'], $this->publicEndpoints)) {
            return $request;
        }

        $authHeader = $request['headers']['Authorization'] ?? '';
        
        if (!$authHeader) {
            throw new \Exception('Authorization header required', 401);
        }

        if (strpos($authHeader, 'Bearer ') === 0) {
            $token = substr($authHeader, 7);
            $request['user'] = $this->validateJWT($token);
        } elseif (strpos($authHeader, 'ApiKey ') === 0) {
            $apiKey = substr($authHeader, 7);
            $request['user'] = $this->validateApiKey($apiKey);
        } else {
            throw new \Exception('Invalid authorization format', 401);
        }

        return $request;
    }

    private function validateJWT(string $token): array
    {
        try {
            $key = $this->config->get('auth.jwt_secret');
            $decoded = JWT::decode($token, new Key($key, 'HS256'));
            return (array) $decoded;
        } catch (\Exception $e) {
            throw new \Exception('Invalid JWT token', 401);
        }
    }

    private function validateApiKey(string $apiKey): array
    {
        $validKeys = $this->config->get('auth.api_keys', []);
        
        if (!in_array($apiKey, $validKeys)) {
            throw new \Exception('Invalid API key', 401);
        }

        return ['type' => 'api_key', 'key' => $apiKey];
    }
}
