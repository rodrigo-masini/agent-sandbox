<?php
// ==============================================
// NETWORK CONTROLLER
// ==============================================

namespace Agtsdbx\Controllers;

use Agtsdbx\Services\NetworkService;
use Agtsdbx\Core\Security\SecurityManager;

class NetworkController extends BaseController
{
    private NetworkService $networkService;
    private SecurityManager $security;

    public function __construct()
    {
        parent::__construct();
        $this->networkService = new NetworkService($this->config, $this->logger);
        $this->security = new SecurityManager($this->config, $this->logger);
    }

    public function request(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            $this->validateRequired($data, ['url']);
            
            $url = $data['url'];
            $method = $data['method'] ?? 'GET';
            $headers = $data['headers'] ?? [];
            $body = $data['data'] ?? null;
            $options = $data['options'] ?? [];
            
            // Security check
            if (!$this->security->isNetworkRequestAllowed($url)) {
                return $this->errorResponse('Network request not allowed', 403);
            }
            
            $result = $this->networkService->makeRequest($url, $method, $headers, $body, $options);
            
            $this->logger->info('Network request made', [
                'url' => $url,
                'method' => $method,
                'user' => $request['user'] ?? 'anonymous'
            ]);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }

    public function download(array $request): array
    {
        try {
            $data = $this->getJsonInput($request);
            $this->validateRequired($data, ['url', 'output']);
            
            $url = $data['url'];
            $output = $data['output'];
            $options = $data['options'] ?? [];
            
            // Security check
            if (!$this->security->isNetworkRequestAllowed($url)) {
                return $this->errorResponse('Download not allowed', 403);
            }
            
            if (!$this->security->isPathAllowed($output)) {
                return $this->errorResponse('Output path not allowed', 403);
            }
            
            $result = $this->networkService->downloadFile($url, $output, $options);
            
            $this->logger->info('File downloaded', [
                'url' => $url,
                'output' => $output,
                'user' => $request['user'] ?? 'anonymous'
            ]);
            
            return $this->successResponse($result);
            
        } catch (\Exception $e) {
            return $this->errorResponse($e->getMessage(), $e->getCode() ?: 500);
        }
    }
}
