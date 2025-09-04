<?php
// ==============================================
// DOCKER SERVICE
// ==============================================

namespace Pandora\Services;

use Pandora\Utils\Config;
use Pandora\Utils\Logger;

class DockerService
{
    private Config $config;
    private Logger $logger;
    private ExecutionService $executor;

    public function __construct(Config $config, Logger $logger)
    {
        $this->config = $config;
        $this->logger = $logger;
        $this->executor = new ExecutionService($config, $logger);
    }

    public function runContainer(string $image, string $command = '', array $options = []): array
    {
        if (!$this->config->get('docker.enabled', true)) {
            throw new \Exception('Docker is disabled', 403);
        }
        
        // Check if image is allowed
        $allowedImages = $this->config->get('docker.allowed_images', []);
        if (!empty($allowedImages) && !in_array($image, $allowedImages)) {
            throw new \Exception('Docker image not allowed', 403);
        }
        
        // Build docker run command
        $dockerCommand = 'docker run';
        
        // Add resource limits
        $limits = $this->config->get('docker.resource_limits', []);
        if (isset($limits['memory'])) {
            $dockerCommand .= ' --memory=' . $limits['memory'];
        }
        if (isset($limits['cpu'])) {
            $dockerCommand .= ' --cpus=' . $limits['cpu'];
        }
        
        // Add security options
        if ($this->config->get('docker.read_only', true)) {
            $dockerCommand .= ' --read-only';
        }
        if ($this->config->get('docker.no_new_privileges', true)) {
            $dockerCommand .= ' --security-opt=no-new-privileges';
        }
        
        // Add network mode
        $networkMode = $this->config->get('docker.network_mode', 'none');
        $dockerCommand .= ' --network=' . $networkMode;
        
        // Add custom options
        if (isset($options['name'])) {
            $dockerCommand .= ' --name=' . escapeshellarg($options['name']);
        }
        if (isset($options['detached']) && $options['detached']) {
            $dockerCommand .= ' -d';
        }
        if (isset($options['environment'])) {
            foreach ($options['environment'] as $key => $value) {
                $dockerCommand .= ' -e ' . escapeshellarg("$key=$value");
            }
        }
        if (isset($options['volumes'])) {
            foreach ($options['volumes'] as $host => $container) {
                $dockerCommand .= ' -v ' . escapeshellarg("$host:$container");
            }
        }
        if (isset($options['ports'])) {
            foreach ($options['ports'] as $host => $container) {
                $dockerCommand .= ' -p ' . escapeshellarg("$host:$container");
            }
        }
        
        // Add image and command
        $dockerCommand .= ' ' . escapeshellarg($image);
        if ($command) {
            $dockerCommand .= ' ' . $command;
        }
        
        // Execute
        $result = $this->executor->execute($dockerCommand, ['timeout' => $options['timeout'] ?? 300]);
        
        if ($result['success'] && isset($options['detached']) && $options['detached']) {
            $containerId = trim($result['stdout']);
            return [
                'success' => true,
                'container_id' => $containerId,
                'image' => $image
            ];
        }
        
        return $result;
    }

    public function listContainers(bool $all = false): array
    {
        $command = 'docker ps';
        if ($all) {
            $command .= ' -a';
        }
        $command .= ' --format json';
        
        $result = $this->executor->execute($command, ['timeout' => 30]);
        
        if (!$result['success']) {
            return [
                'success' => false,
                'error' => $result['stderr']
            ];
        }
        
        $containers = [];
        $lines = explode("\n", trim($result['stdout']));
        
        foreach ($lines as $line) {
            if (empty($line)) continue;
            
            $container = json_decode($line, true);
            if ($container) {
                $containers[] = [
                    'id' => $container['ID'] ?? '',
                    'image' => $container['Image'] ?? '',
                    'name' => $container['Names'] ?? '',
                    'status' => $container['Status'] ?? '',
                    'created' => $container['CreatedAt'] ?? '',
                    'ports' => $container['Ports'] ?? ''
                ];
            }
        }
        
        return [
            'success' => true,
            'containers' => $containers
        ];
    }
}
