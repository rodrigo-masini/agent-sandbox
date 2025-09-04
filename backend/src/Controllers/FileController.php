<?php

namespace Agtsdbx\Controllers;

use Agtsdbx\Services\FileService;
use Agtsdbx\Core\Security\SecurityManager;

class FileController extends BaseController
{
    private FileService $fileService;
    private SecurityManager $security;

    public function __construct()
    {
        parent::__construct();
        $this->fileService = new FileService($this->config, $this->logger);
        $this->security = new SecurityManager($this->config);
    }

    public function write(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            $this->validateRequired($data, ['filePath', 'content']);
            
            $filePath = $data['filePath'];
            $content = $data['content'];
            $options = $data['options'] ?? [];
            
            // Security validation
            if (!$this->security->isPathAllowed($filePath)) {
                return $this->errorResponse('Path not allowed', 403);
            }
            
            $result = $this->fileService->write($filePath, $content, $options);
            
            $this->logger->info('File written', [
                'path' => $filePath,
                'size' => strlen($content),
                'user' => $request['user'] ?? 'anonymous',
            ]);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }

    public function read(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            $this->validateRequired($data, ['filePath']);
            
            $filePath = $data['filePath'];
            $options = $data['options'] ?? [];
            
            if (!$this->security->isPathAllowed($filePath)) {
                return $this->errorResponse('Path not allowed', 403);
            }
            
            $result = $this->fileService->read($filePath, $options);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }

    public function list(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            $path = $data['path'] ?? '.';
            $options = $data['options'] ?? [];
            
            if (!$this->security->isPathAllowed($path)) {
                return $this->errorResponse('Path not allowed', 403);
            }
            
            $result = $this->fileService->list($path, $options);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }

    public function delete(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            $this->validateRequired($data, ['filePath']);
            
            $filePath = $data['filePath'];
            
            if (!$this->security->isPathAllowed($filePath)) {
                return $this->errorResponse('Path not allowed', 403);
            }
            
            $result = $this->fileService->delete($filePath);
            
            $this->logger->info('File deleted', [
                'path' => $filePath,
                'user' => $request['user'] ?? 'anonymous',
            ]);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }
}
