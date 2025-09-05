<?php
// ==============================================
// DOCKER CONTROLLER
// ==============================================

namespace Agtsdbx\Controllers;

use Agtsdbx\Services\DockerService;
use Agtsdbx\Core\Security\SecurityManager;

class DockerController extends BaseController
{
    private DockerService $dockerService;

    public function __construct()
    {
        parent::__construct();
        $this->dockerService = new DockerService($this->config, $this->logger);
    }

    public function run(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            $this->validateRequired($data, ['image']);
            
            $image = $data['image'];
            $command = $data['command'] ?? '';
            $options = $data['options'] ?? [];
            
            $result = $this->dockerService->runContainer($image, $command, $options);
            
            $this->logger->info('Docker container started', [
                'image' => $image,
                'container_id' => $result['container_id'] ?? null,
                'user' => $request['user'] ?? 'anonymous'
            ]);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }

    public function list(array $request): array
    {
        try {
            $all = isset($_GET['all']) && $_GET['all'] === 'true';
            
            $result = $this->dockerService->listContainers($all);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }

    public function remove(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            $this->validateRequired($data, ['container']);
            
            $container = $data['container'];
            $force = $data['force'] ?? false;
            
            $command = sprintf(
                'docker rm %s %s',
                $force ? '-f' : '',
                escapeshellarg($container)
            );
            
            $executor = new \Agtsdbx\Services\ExecutionService($this->config, $this->logger);
            $result = $executor->execute($command, ['timeout' => 30]);
            
            if ($result['success']) {
                $this->logger->info('Docker container removed', [
                    'container' => $container,
                    'user' => $request['user'] ?? 'anonymous'
                ]);
                
                return $this->successResponse(['container' => $container, 'removed' => true]);
            } else {
                return $this->errorResponse('Failed to remove container: ' . $result['stderr'], 500);
            }
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }
}
