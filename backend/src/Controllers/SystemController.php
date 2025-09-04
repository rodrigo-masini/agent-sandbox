<?php
// ==============================================
// SYSTEM CONTROLLER
// ==============================================

namespace Pandora\Controllers;

use Pandora\Services\SystemService;

class SystemController extends BaseController
{
    private SystemService $systemService;

    public function __construct()
    {
        parent::__construct();
        $this->systemService = new SystemService($this->config, $this->logger);
    }

    public function health(array $request): array
    {
        try {
            $health = $this->systemService->getHealthStatus();
            
            if ($health['status'] === 'healthy') {
                return $this->successResponse($health, 'System is healthy');
            } else {
                return $this->errorResponse('System is unhealthy', 503);
            }
        } catch (\Exception $e) {
            return $this->errorResponse('Health check failed: ' . $e->getMessage(), 500);
        }
    }

    public function info(array $request): array
    {
        try {
            $info = $this->systemService->getSystemInfo();
            return $this->successResponse($info);
        } catch (\Exception $e) {
            return $this->errorResponse('Failed to get system info: ' . $e->getMessage(), 500);
        }
    }

    public function metrics(array $request): array
    {
        try {
            $metrics = $this->systemService->getMetrics();
            return $this->successResponse($metrics);
        } catch (\Exception $e) {
            return $this->errorResponse('Failed to get metrics: ' . $e->getMessage(), 500);
        }
    }
}
