<?php

namespace Agtsdbx\Core;

use Agtsdbx\Core\Middleware\AuthMiddleware;
use Agtsdbx\Core\Middleware\RateLimitMiddleware;
use Agtsdbx\Core\Middleware\LoggingMiddleware;
use Agtsdbx\Core\Middleware\ValidationMiddleware;
use Agtsdbx\Core\Middleware\SecurityMiddleware;
use Agtsdbx\Utils\Logger;
use Agtsdbx\Utils\Config;

class Application
{
    private Router $router;
    private Logger $logger;
    private Config $config;
    private array $middleware = [];

    public function __construct()
    {
        $this->config = Config::getInstance();
        $this->logger = new Logger($this->config);
        $this->router = new Router($this->logger);
        $this->initializeMiddleware();
        $this->registerRoutes();
    }

    private function initializeMiddleware(): void
    {
        $this->middleware = [
            new SecurityMiddleware($this->config),
            new LoggingMiddleware($this->logger),
            new AuthMiddleware($this->config),
            new RateLimitMiddleware($this->config),
            new ValidationMiddleware($this->config),
        ];
    }

    private function registerRoutes(): void
    {
        // Health check endpoint
        $this->router->get('/health', 'SystemController@health');
        
        // API endpoints
        $this->router->post('/api/v1/exec', 'ExecutionController@execute');
        $this->router->post('/api/v1/file/write', 'FileController@write');
        $this->router->post('/api/v1/file/read', 'FileController@read');
        $this->router->post('/api/v1/file/list', 'FileController@list');
        $this->router->delete('/api/v1/file/delete', 'FileController@delete');
        
        // System endpoints
        $this->router->get('/api/v1/system/info', 'SystemController@info');
        $this->router->get('/api/v1/system/metrics', 'SystemController@metrics');
        
        // Docker endpoints
        $this->router->post('/api/v1/docker/run', 'DockerController@run');
        $this->router->get('/api/v1/docker/list', 'DockerController@list');
        $this->router->delete('/api/v1/docker/remove', 'DockerController@remove');
        
        // Network endpoints
        $this->router->post('/api/v1/network/request', 'NetworkController@request');
        $this->router->post('/api/v1/network/download', 'NetworkController@download');
        
        // Database endpoints
        $this->router->post('/api/v1/database/query', 'DatabaseController@query');
        $this->router->post('/api/v1/database/execute', 'DatabaseController@execute');
    }

    public function run(): void
    {
        try {
            $request = $this->createRequest();
            $response = $this->handleRequest($request);
            $this->sendResponse($response);
        } catch (\Throwable $e) {
            $this->handleError($e);
        }
    }

    private function createRequest(): array
    {
        return [
            'method' => $_SERVER['REQUEST_METHOD'],
            'uri' => parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH),
            'query' => $_GET,
            'body' => file_get_contents('php://input'),
            'headers' => getallheaders(),
            'ip' => $_SERVER['REMOTE_ADDR'] ?? 'unknown',
            'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? 'unknown',
            'timestamp' => microtime(true),
        ];
    }

    private function handleRequest(array $request): array
    {
        // Apply middleware
        foreach ($this->middleware as $middleware) {
            $request = $middleware->handle($request);
        }

        // Route the request
        return $this->router->dispatch($request);
    }

    private function sendResponse(array $response): void
    {
        http_response_code($response['status'] ?? 200);
        
        foreach ($response['headers'] ?? [] as $header => $value) {
            header("$header: $value");
        }

        if (isset($response['body'])) {
            echo is_array($response['body']) ? json_encode($response['body']) : $response['body'];
        }
    }

    private function handleError(\Throwable $e): void
    {
        $this->logger->error('Application error', [
            'message' => $e->getMessage(),
            'file' => $e->getFile(),
            'line' => $e->getLine(),
            'trace' => $e->getTraceAsString(),
        ]);

        http_response_code(500);
        header('Content-Type: application/json');
        echo json_encode([
            'error' => 'Internal server error',
            'message' => $this->config->get('app.debug') ? $e->getMessage() : 'An error occurred',
            'timestamp' => date('c'),
        ]);
    }
}
