<?php
// ==============================================
// BASE CONTROLLER
// ==============================================

namespace Agtsdbx\Controllers;

use Agtsdbx\Utils\Config;
use Agtsdbx\Utils\Logger;

abstract class BaseController
{
    protected Config $config;
    protected Logger $logger;

    public function __construct()
    {
        $this->config = new Config();
        $this->logger = new Logger($this->config);
    }

    protected function getJsonInput(array $request): array
    {
        $body = $request['body'] ?? '';
        
        if (empty($body)) {
            return [];
        }
        
        $data = json_decode($body, true);
        
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new \Exception('Invalid JSON input: ' . json_last_error_msg(), 400);
        }
        
        return $data ?? [];
    }

    protected function validateRequired(array $data, array $required): void
    {
        foreach ($required as $field) {
            if (!isset($data[$field]) || $data[$field] === '') {
                throw new \Exception("Missing required field: $field", 400);
            }
        }
    }

    /**
     * @param mixed $data
     */
    protected function successResponse($data = null, string $message = 'Success'): array
    {
        return [
            'status' => 200,
            'headers' => ['Content-Type' => 'application/json'],
            'body' => [
                'success' => true,
                'message' => $message,
                'data' => $data,
                'timestamp' => date('c')
            ]
        ];
    }

    protected function errorResponse(string $message, int $code = 400): array
    {
        return [
            'status' => $code,
            'headers' => ['Content-Type' => 'application/json'],
            'body' => [
                'success' => false,
                'error' => $message,
                'timestamp' => date('c')
            ]
        ];
    }
}