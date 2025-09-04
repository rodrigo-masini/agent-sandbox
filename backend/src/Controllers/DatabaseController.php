<?php
// ==============================================
// DATABASE CONTROLLER
// ==============================================

namespace Agtsdbx\Controllers;

use Agtsdbx\Services\DatabaseService;
use Agtsdbx\Core\Security\SecurityManager;

class DatabaseController extends BaseController
{
    private DatabaseService $databaseService;
    private SecurityManager $security;

    public function __construct()
    {
        parent::__construct();
        $this->databaseService = new DatabaseService($this->config, $this->logger);
        $this->security = new SecurityManager($this->config, $this->logger);
    }

    public function query(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            $this->validateRequired($data, ['query']);
            
            $query = $data['query'];
            $params = $data['params'] ?? [];
            $database = $data['database'] ?? 'default';
            
            // Security: Only allow SELECT queries
            if (!preg_match('/^\s*SELECT/i', $query)) {
                return $this->errorResponse('Only SELECT queries are allowed', 403);
            }
            
            $result = $this->databaseService->query($query, $params, $database);
            
            $this->logger->info('Database query executed', [
                'database' => $database,
                'query_type' => 'SELECT',
                'user' => $request['user'] ?? 'anonymous'
            ]);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }

    public function execute(array $request): array
    {
        try {
            // Check if user has permission
            if (!isset($request['user']) || $request['user']['role'] !== 'admin') {
                return $this->errorResponse('Admin access required', 403);
            }
            
            $data = $this->getJsonInput($request);
            $this->validateRequired($data, ['query']);
            
            $query = $data['query'];
            $params = $data['params'] ?? [];
            $database = $data['database'] ?? 'default';
            
            $result = $this->databaseService->execute($query, $params, $database);
            
            $this->logger->warning('Database execute operation', [
                'database' => $database,
                'query_type' => $this->getQueryType($query),
                'user' => $request['user'] ?? 'anonymous'
            ]);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }

    private function getQueryType(string $query): string
    {
        $query = trim($query);
        $firstWord = strtoupper(explode(' ', $query)[0]);
        return $firstWord;
    }
}
