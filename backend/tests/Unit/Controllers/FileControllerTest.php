<?php

namespace Agtsdbx\Tests\Unit\Controllers;

use PHPUnit\Framework\TestCase;
use Agtsdbx\Controllers\FileController;
use Agtsdbx\Services\FileService;
use Agtsdbx\Core\Security\SecurityManager;
use Agtsdbx\Utils\Config;
use Agtsdbx\Utils\Logger;
use Mockery;

class FileControllerTest extends TestCase
{
    private $controller;
    private $fileService;
    private $security;
    private $config;
    private $logger;

    protected function setUp(): void
    {
        $this->config = Mockery::mock(Config::class);
        $this->logger = Mockery::mock(Logger::class);
        $this->fileService = Mockery::mock(FileService::class);
        $this->security = Mockery::mock(SecurityManager::class);
        
        $this->controller = Mockery::mock(FileController::class)->makePartial();
        $this->controller->shouldAllowMockingProtectedMethods();
        
        // Inject mocks using reflection
        $reflection = new \ReflectionClass($this->controller);
        
        $fileServiceProp = $reflection->getProperty('fileService');
        $fileServiceProp->setAccessible(true);
        $fileServiceProp->setValue($this->controller, $this->fileService);
        
        $securityProp = $reflection->getProperty('security');
        $securityProp->setAccessible(true);
        $securityProp->setValue($this->controller, $this->security);
    }

    protected function tearDown(): void
    {
        Mockery::close();
    }

    public function testWriteFileSuccess()
    {
        $request = [
            'body' => json_encode([
                'filePath' => '/app/WORKDIR/test.txt',
                'content' => 'test content'
            ])
        ];

        $this->security->shouldReceive('isPathAllowed')
            ->with('/app/WORKDIR/test.txt')
            ->andReturn(true);

        $this->fileService->shouldReceive('write')
            ->with('/app/WORKDIR/test.txt', 'test content', [])
            ->andReturn(['success' => true, 'path' => '/app/WORKDIR/test.txt']);

        $this->logger->shouldReceive('info')->once();

        $response = $this->controller->write($request);

        $this->assertEquals(200, $response['status']);
        $this->assertTrue($response['body']['success']);
    }

    public function testWriteFilePathNotAllowed()
    {
        $request = [
            'body' => json_encode([
                'filePath' => '/etc/passwd',
                'content' => 'malicious content'
            ])
        ];

        $this->security->shouldReceive('isPathAllowed')
            ->with('/etc/passwd')
            ->andReturn(false);

        $response = $this->controller->write($request);

        $this->assertEquals(403, $response['status']);
        $this->assertFalse($response['body']['success']);
        $this->assertEquals('Path not allowed', $response['body']['error']);
    }

    public function testReadFileNotFound()
    {
        $request = [
            'body' => json_encode([
                'filePath' => '/app/WORKDIR/nonexistent.txt'
            ])
        ];

        $this->security->shouldReceive('isPathAllowed')
            ->with('/app/WORKDIR/nonexistent.txt')
            ->andReturn(true);

        $this->fileService->shouldReceive('read')
            ->andThrow(new \Exception('File not found', 404));

        $response = $this->controller->read($request);

        $this->assertEquals(404, $response['status']);
        $this->assertEquals('File not found', $response['body']['error']);
    }

    public function testDeleteFileRequiresValidPath()
    {
        $request = [
            'body' => json_encode([
                'filePath' => '../../../etc/passwd'
            ])
        ];

        $this->security->shouldReceive('isPathAllowed')
            ->with('../../../etc/passwd')
            ->andReturn(false);

        $response = $this->controller->delete($request);

        $this->assertEquals(403, $response['status']);
        $this->assertEquals('Path not allowed', $response['body']['error']);
    }
}