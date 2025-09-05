<?php

namespace Agtsdbx\Tests\Integration;

use PHPUnit\Framework\TestCase;

class APIIntegrationTest extends TestCase
{
    private string $baseUrl = 'http://localhost:8000';
    private string $apiKey = 'test_api_key';

    protected function setUp(): void
    {
        // Ensure test environment is running
        $this->checkServiceAvailable();
    }

    private function checkServiceAvailable(): void
    {
        $ch = curl_init($this->baseUrl . '/health');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode !== 200) {
            $this->markTestSkipped('Backend service is not available');
        }
    }

    public function testHealthEndpoint()
    {
        $response = $this->makeRequest('GET', '/health');
        
        $this->assertEquals(200, $response['status']);
        $this->assertEquals('healthy', $response['body']['status']);
        $this->assertArrayHasKey('checks', $response['body']);
    }

    public function testAuthenticationRequired()
    {
        $response = $this->makeRequest('POST', '/api/v1/exec', [], false);
        
        $this->assertEquals(401, $response['status']);
        $this->assertStringContainsString('Authorization header required', $response['body']['error'] ?? '');
    }

    public function testExecuteSimpleCommand()
    {
        $response = $this->makeRequest('POST', '/api/v1/exec', [
            'command' => 'echo "test"'
        ]);
        
        $this->assertEquals(200, $response['status']);
        $this->assertTrue($response['body']['success']);
        $this->assertStringContainsString('test', $response['body']['data']['stdout']);
    }

    public function testFileOperationWorkflow()
    {
        $testFile = '/app/WORKDIR/test_' . uniqid() . '.txt';
        $content = 'Test content ' . time();
        
        // Write file
        $writeResponse = $this->makeRequest('POST', '/api/v1/file/write', [
            'filePath' => $testFile,
            'content' => $content
        ]);
        
        $this->assertEquals(200, $writeResponse['status']);
        $this->assertTrue($writeResponse['body']['success']);
        
        // Read file
        $readResponse = $this->makeRequest('POST', '/api/v1/file/read', [
            'filePath' => $testFile
        ]);
        
        $this->assertEquals(200, $readResponse['status']);
        $this->assertEquals($content, $readResponse['body']['data']['content']);
        
        // Delete file
        $deleteResponse = $this->makeRequest('DELETE', '/api/v1/file/delete', [
            'filePath' => $testFile
        ]);
        
        $this->assertEquals(200, $deleteResponse['status']);
        $this->assertTrue($deleteResponse['body']['data']['deleted']);
        
        // Verify deletion
        $verifyResponse = $this->makeRequest('POST', '/api/v1/file/read', [
            'filePath' => $testFile
        ]);
        
        $this->assertEquals(404, $verifyResponse['status']);
    }

    public function testRateLimiting()
    {
        // Make many rapid requests
        $responses = [];
        for ($i = 0; $i < 100; $i++) {
            $responses[] = $this->makeRequest('GET', '/api/v1/system/info');
        }
        
        // Check if any were rate limited
        $rateLimited = array_filter($responses, fn($r) => $r['status'] === 429);
        
        $this->assertNotEmpty($rateLimited, 'Rate limiting should trigger after many requests');
    }

    public function testConcurrentCommandExecution()
    {
        $commands = [];
        for ($i = 0; $i < 5; $i++) {
            $commands[] = [
                'url' => $this->baseUrl . '/api/v1/exec',
                'data' => json_encode(['command' => "echo 'Process $i' && sleep 1"])
            ];
        }
        
        $multiHandle = curl_multi_init();
        $curlHandles = [];
        
        foreach ($commands as $cmd) {
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $cmd['url']);
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $cmd['data']);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_HTTPHEADER, [
                'Content-Type: application/json',
                'Authorization: ApiKey ' . $this->apiKey
            ]);
            
            curl_multi_add_handle($multiHandle, $ch);
            $curlHandles[] = $ch;
        }
        
        // Execute all requests
        $running = null;
        do {
            curl_multi_exec($multiHandle, $running);
            curl_multi_select($multiHandle);
        } while ($running > 0);
        
        // Check all succeeded
        foreach ($curlHandles as $i => $ch) {
            $response = curl_multi_getcontent($ch);
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            
            $this->assertEquals(200, $httpCode, "Request $i failed");
            
            $body = json_decode($response, true);
            $this->assertTrue($body['success'], "Command $i execution failed");
            
            curl_multi_remove_handle($multiHandle, $ch);
            curl_close($ch);
        }
        
        curl_multi_close($multiHandle);
    }

    private function makeRequest(string $method, string $endpoint, array $data = [], bool $auth = true): array
    {
        $ch = curl_init($this->baseUrl . $endpoint);
        
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
        
        $headers = ['Content-Type: application/json'];
        if ($auth) {
            $headers[] = 'Authorization: ApiKey ' . $this->apiKey;
        }
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        
        if (!empty($data)) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        }
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        return [
            'status' => $httpCode,
            'body' => json_decode($response, true)
        ];
    }
}