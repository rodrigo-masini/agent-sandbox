<?php

namespace Agtsdbx\Tests\Unit\Core\Middleware;

use PHPUnit\Framework\TestCase;
use Agtsdbx\Core\Middleware\AuthMiddleware;
use Agtsdbx\Utils\Config;
use Firebase\JWT\JWT;
use Firebase\JWT\Key;
use Mockery;

class AuthMiddlewareTest extends TestCase
{
    private AuthMiddleware $middleware;
    private Config $config;

    protected function setUp(): void
    {
        $this->config = Mockery::mock(Config::class);
        $this->config->shouldReceive('get')
            ->with('auth.jwt_secret')
            ->andReturn('test_secret_key');
        $this->config->shouldReceive('get')
            ->with('auth.api_keys', [])
            ->andReturn(['valid_api_key_1', 'valid_api_key_2']);
            
        $this->middleware = new AuthMiddleware($this->config);
    }

    protected function tearDown(): void
    {
        Mockery::close();
    }

    public function testPublicEndpointsDoNotRequireAuth()
    {
        $publicEndpoints = ['/health', '/api/v1/system/info'];
        
        foreach ($publicEndpoints as $endpoint) {
            $request = ['uri' => $endpoint, 'headers' => []];
            $result = $this->middleware->handle($request);
            $this->assertEquals($request, $result);
        }
    }

    public function testValidJWTToken()
    {
        $payload = [
            'user_id' => 1,
            'role' => 'admin',
            'exp' => time() + 3600
        ];
        
        $token = JWT::encode($payload, 'test_secret_key', 'HS256');
        
        $request = [
            'uri' => '/api/v1/exec',
            'headers' => ['Authorization' => 'Bearer ' . $token]
        ];
        
        $result = $this->middleware->handle($request);
        
        $this->assertArrayHasKey('user', $result);
        $this->assertEquals(1, $result['user']['user_id']);
        $this->assertEquals('admin', $result['user']['role']);
    }

    public function testExpiredJWTToken()
    {
        $payload = [
            'user_id' => 1,
            'exp' => time() - 3600  // Expired 1 hour ago
        ];
        
        $token = JWT::encode($payload, 'test_secret_key', 'HS256');
        
        $request = [
            'uri' => '/api/v1/exec',
            'headers' => ['Authorization' => 'Bearer ' . $token]
        ];
        
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage('Invalid JWT token');
        $this->expectExceptionCode(401);
        
        $this->middleware->handle($request);
    }

    public function testValidApiKey()
    {
        $request = [
            'uri' => '/api/v1/exec',
            'headers' => ['Authorization' => 'ApiKey valid_api_key_1']
        ];
        
        $result = $this->middleware->handle($request);
        
        $this->assertArrayHasKey('user', $result);
        $this->assertEquals('api_key', $result['user']['type']);
        $this->assertEquals('valid_api_key_1', $result['user']['key']);
    }

    public function testInvalidApiKey()
    {
        $request = [
            'uri' => '/api/v1/exec',
            'headers' => ['Authorization' => 'ApiKey invalid_key']
        ];
        
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage('Invalid API key');
        $this->expectExceptionCode(401);
        
        $this->middleware->handle($request);
    }

    public function testMissingAuthorizationHeader()
    {
        $request = [
            'uri' => '/api/v1/exec',
            'headers' => []
        ];
        
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage('Authorization header required');
        $this->expectExceptionCode(401);
        
        $this->middleware->handle($request);
    }
}