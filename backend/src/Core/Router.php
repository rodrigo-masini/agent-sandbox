<?php

namespace Agtsdbx\Core;

use Agtsdbx\Utils\Logger;

class Router
{
    private array $routes = [];

    public function __construct(Logger $logger)
    {
        // Use logger for initialization or remove parameter if not needed
        $logger->debug('Router initialized');
    }

    public function get(string $path, string $handler): void
    {
        $this->addRoute('GET', $path, $handler);
    }

    public function post(string $path, string $handler): void
    {
        $this->addRoute('POST', $path, $handler);
    }

    public function put(string $path, string $handler): void
    {
        $this->addRoute('PUT', $path, $handler);
    }

    public function delete(string $path, string $handler): void
    {
        $this->addRoute('DELETE', $path, $handler);
    }

    private function addRoute(string $method, string $path, string $handler): void
    {
        $this->routes[] = [
            'method' => $method,
            'path' => $path,
            'handler' => $handler,
            'pattern' => $this->pathToPattern($path),
        ];
    }

    private function pathToPattern(string $path): string
    {
        // Convert path parameters like {id} to regex patterns
        $pattern = preg_replace('/\{([^}]+)\}/', '(?P<$1>[^/]+)', $path);
        return '#^' . $pattern . '$#';
    }

    public function dispatch(array $request): array
    {
        $method = $request['method'];
        $path = $request['uri'];

        foreach ($this->routes as $route) {
            if ($route['method'] === $method && preg_match($route['pattern'], $path, $matches)) {
                return $this->callHandler($route['handler'], $request, $matches);
            }
        }

        return [
            'status' => 404,
            'headers' => ['Content-Type' => 'application/json'],
            'body' => ['error' => 'Endpoint not found', 'path' => $path],
        ];
    }

    private function callHandler(string $handler, array $request, array $matches): array
    {
        [$controllerName, $methodName] = explode('@', $handler);
        $controllerClass = "Agtsdbx\\Controllers\\$controllerName";

        if (!class_exists($controllerClass)) {
            throw new \Exception("Controller $controllerClass not found");
        }

        $controller = new $controllerClass();
        
        if (!method_exists($controller, $methodName)) {
            throw new \Exception("Method $methodName not found in $controllerClass");
        }

        // Extract path parameters
        $params = array_filter($matches, 'is_string', ARRAY_FILTER_USE_KEY);
        $request['params'] = $params;

        return $controller->$methodName($request);
    }
}
