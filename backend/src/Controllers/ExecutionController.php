<?php

namespace Pandora\Controllers;

use Pandora\Services\ExecutionService;
use Pandora\Core\Security\SecurityManager;
use Pandora\Utils\Logger;

class ExecutionController extends BaseController
{
    private ExecutionService $executionService;
    private SecurityManager $security;

    public function __construct()
    {
        parent::__construct();
        $this->executionService = new ExecutionService($this->config, $this->logger);
        $this->security = new SecurityManager($this->config);
    }

    public function execute(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            
            // Validate required fields
            $this->validateRequired($data, ['command']);
            
            $command = $data['command'];
            $options = $data['options'] ?? [];
            
            // Security validation
            if (!$this->security->isCommandAllowed($command)) {
                return $this->errorResponse('Command not allowed', 403);
            }
            
            // Sanitize command
            $sanitizedCommand = $this->security->sanitizeCommand($command);
            
            // Execute command
            $result = $this->executionService->execute($sanitizedCommand, $options);
            
            // Log execution
            $this->logger->info('Command executed', [
                'command' => $sanitizedCommand,
                'user' => $request['user'] ?? 'anonymous',
                'duration' => $result['duration'] ?? 0,
                'exit_code' => $result['exit_code'] ?? 0,
            ]);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            $this->logger->error('Execution failed', [
                'error' => $e->getMessage(),
                'command' => $command ?? 'unknown',
            ]);
            
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }
}
