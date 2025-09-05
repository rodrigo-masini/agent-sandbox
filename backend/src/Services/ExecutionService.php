<?php
namespace Agtsdbx\Services;

use Agtsdbx\Utils\Config;
use Agtsdbx\Utils\Logger;
use Agtsdbx\Core\Security\Sandbox;

class ExecutionService
{
    private Config $config;
    // Remove $logger property if not used, or use it for logging
    private Sandbox $sandbox;
    private string $workdir;

    public function __construct(Config $config, Logger $logger)
    {
        $this->config = $config;
        // Don't store logger if not using it
        $this->sandbox = new Sandbox($config);
        $this->workdir = $config->get('workdir', '/app/WORKDIR');
        
        // Log initialization
        $logger->debug('ExecutionService initialized', ['workdir' => $this->workdir]);
    }

    public function execute(string $command, array $options = []): array
    {
        $startTime = microtime(true);
        
        // Get options
        $timeout = $options['timeout'] ?? $this->config->get('commands.timeout', 300);
        $workingDirectory = $options['working_directory'] ?? $this->workdir;
        $environment = $options['environment'] ?? [];
        $captureOutput = $options['capture_output'] ?? true;
        
        // Ensure working directory exists and is safe
        if (!is_dir($workingDirectory)) {
            mkdir($workingDirectory, 0755, true);
        }
        
        // Build command with timeout
        $fullCommand = sprintf(
            'timeout %d bash -c %s',
            $timeout,
            escapeshellarg($command)
        );
        
        // Execute in sandbox if enabled
        if ($this->config->get('sandbox.enabled', true)) {
            $fullCommand = $this->sandbox->wrapCommand($fullCommand);
        }
        
        // Execute command
        $descriptorspec = [
            0 => ["pipe", "r"],  // stdin
            1 => ["pipe", "w"],  // stdout
            2 => ["pipe", "w"]   // stderr
        ];
        
        $process = proc_open(
            $fullCommand,
            $descriptorspec,
            $pipes,
            $workingDirectory,
            array_merge($_ENV, $environment)
        );
        
        if (!is_resource($process)) {
            throw new \Exception('Failed to execute command');
        }
        
        // Close stdin
        fclose($pipes[0]);
        
        // Read output
        $stdout = $captureOutput ? stream_get_contents($pipes[1]) : '';
        $stderr = $captureOutput ? stream_get_contents($pipes[2]) : '';
        
        fclose($pipes[1]);
        fclose($pipes[2]);
        
        // Get exit code
        $exitCode = proc_close($process);
        
        $duration = microtime(true) - $startTime;
        
        return [
            'stdout' => $stdout,
            'stderr' => $stderr,
            'exit_code' => $exitCode,
            'success' => $exitCode === 0,
            'duration' => $duration,
            'command' => $command
        ];
    }
}