<?php

namespace Agtsdbx\Tests\Unit\Services;

use PHPUnit\Framework\TestCase;
use Agtsdbx\Services\ExecutionService;
use Agtsdbx\Utils\Config;
use Agtsdbx\Utils\Logger;
use Mockery;

class ExecutionServiceTest extends TestCase
{
    private $config;
    private $logger;
    private $service;

    protected function setUp(): void
    {
        $this->config = Mockery::mock(Config::class);
        $this->logger = Mockery::mock(Logger::class);
        
        // Add ALL necessary config expectations
        $this->config->shouldReceive('get')
            ->with('workdir', '/app/WORKDIR')
            ->andReturn('/tmp/test_workdir');
            
        $this->config->shouldReceive('get')
            ->with('commands.timeout', 300)
            ->andReturn(300);
            
        $this->config->shouldReceive('get')
            ->with('sandbox.enabled', true)
            ->andReturn(false);
            
        // Add expectations for Sandbox config calls
        $this->config->shouldReceive('get')
            ->with('sandbox.allow_network', false)
            ->andReturn(false);
            
        $this->config->shouldReceive('get')
            ->with('workdir', '/app/WORKDIR')
            ->andReturn('/tmp/test_workdir');
            
        $this->config->shouldReceive('get')
            ->with('sandbox.docker_image', 'alpine:latest')
            ->andReturn('alpine:latest');
            
        // Add logger debug expectation
        $this->logger->shouldReceive('debug')->withAnyArgs();
        
        $this->service = new ExecutionService($this->config, $this->logger);
    }

    protected function tearDown(): void
    {
        Mockery::close();
    }

    public function testExecuteSimpleCommand()
    {
        $result = $this->service->execute('echo "test"');
        
        $this->assertIsArray($result);
        $this->assertArrayHasKey('stdout', $result);
        $this->assertArrayHasKey('stderr', $result);
        $this->assertArrayHasKey('exit_code', $result);
        $this->assertArrayHasKey('success', $result);
        $this->assertEquals(0, $result['exit_code']);
        $this->assertTrue($result['success']);
        $this->assertStringContainsString('test', $result['stdout']);
    }

    public function testExecuteWithTimeout()
    {
        $result = $this->service->execute('sleep 10', ['timeout' => 1]);
        
        $this->assertFalse($result['success']);
        $this->assertNotEquals(0, $result['exit_code']);
    }

    public function testExecuteWithWorkingDirectory()
    {
        $tempDir = sys_get_temp_dir();
        $result = $this->service->execute('pwd', ['working_directory' => $tempDir]);
        
        $this->assertTrue($result['success']);
        $this->assertStringContainsString(basename($tempDir), $result['stdout']);
    }

    public function testExecuteWithEnvironmentVariables()
    {
        $result = $this->service->execute('echo $TEST_VAR', [
            'environment' => ['TEST_VAR' => 'test_value']
        ]);
        
        $this->assertTrue($result['success']);
        $this->assertStringContainsString('test_value', $result['stdout']);
    }

    public function testExecuteInvalidCommand()
    {
        $result = $this->service->execute('this_command_does_not_exist');
        
        $this->assertFalse($result['success']);
        $this->assertNotEquals(0, $result['exit_code']);
    }
}