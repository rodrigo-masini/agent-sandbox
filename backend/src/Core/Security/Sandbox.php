<?php
// ==============================================
// SANDBOX IMPLEMENTATION
// ==============================================

namespace Pandora\Core\Security;

use Pandora\Utils\Config;

class Sandbox
{
    private Config $config;
    private bool $enabled;
    private array $restrictions;

    public function __construct(Config $config)
    {
        $this->config = $config;
        $this->enabled = $config->get('sandbox.enabled', true);
        $this->restrictions = $this->loadRestrictions();
    }

    public function wrapCommand(string $command): string
    {
        if (!$this->enabled) {
            return $command;
        }
        
        // Use firejail if available for sandboxing
        if ($this->hasFirejail()) {
            return $this->wrapWithFirejail($command);
        }
        
        // Use Docker if available
        if ($this->hasDocker()) {
            return $this->wrapWithDocker($command);
        }
        
        // Fallback to basic restrictions
        return $this->applyBasicRestrictions($command);
    }

    private function wrapWithFirejail(string $command): string
    {
        $options = [
            '--noprofile',      // No saved profiles
            '--noroot',         // No root user
            '--caps.drop=all',  // Drop all capabilities
            '--nonewprivs',     // No new privileges
            '--nogroups',       // No supplementary groups
            '--nosound',        // No sound
            '--no3d',           // No 3D acceleration
            '--nodvd',          // No DVD
            '--notv',           // No TV
            '--novideo',        // No video
            '--machine-id',     // Random machine ID
            '--disable-mnt',    // Disable /mnt
            '--private-tmp',    // Private /tmp
            '--private-dev'     // Private /dev
        ];
        
        // Add network restrictions
        if (!$this->config->get('sandbox.allow_network', false)) {
            $options[] = '--net=none';
        }
        
        // Add filesystem restrictions
        $workdir = $this->config->get('workdir', '/app/WORKDIR');
        $options[] = "--whitelist=$workdir";
        $options[] = '--read-only=/';
        $options[] = "--read-write=$workdir";
        
        return 'firejail ' . implode(' ', $options) . ' -- ' . $command;
    }

    private function wrapWithDocker(string $command): string
    {
        $image = $this->config->get('sandbox.docker_image', 'alpine:latest');
        $workdir = $this->config->get('workdir', '/app/WORKDIR');
        
        $dockerCmd = 'docker run --rm';
        $dockerCmd .= ' --network=none';           // No network
        $dockerCmd .= ' --read-only';              // Read-only root
        $dockerCmd .= ' --security-opt=no-new-privileges';
        $dockerCmd .= ' --cap-drop=ALL';           // Drop all capabilities
        $dockerCmd .= ' --memory=256m';            // Memory limit
        $dockerCmd .= ' --cpus=0.5';               // CPU limit
        $dockerCmd .= " -v $workdir:/workspace:rw"; // Mount workspace
        $dockerCmd .= ' -w /workspace';            // Set working directory
        $dockerCmd .= " $image";
        $dockerCmd .= ' sh -c ' . escapeshellarg($command);
        
        return $dockerCmd;
    }

    private function applyBasicRestrictions(string $command): string
    {
        // Set resource limits using ulimit
        $limits = [
            'ulimit -t 300',     // CPU time limit (300 seconds)
            'ulimit -v 524288',  // Virtual memory (512MB)
            'ulimit -f 102400',  // File size (100MB)
            'ulimit -n 256',     // Number of open files
            'ulimit -u 32'       // Number of processes
        ];
        
        return implode('; ', $limits) . '; ' . $command;
    }

    private function hasFirejail(): bool
    {
        exec('which firejail 2>/dev/null', $output, $returnCode);
        return $returnCode === 0;
    }

    private function hasDocker(): bool
    {
        if (!$this->config->get('docker.enabled', true)) {
            return false;
        }
        
        exec('which docker 2>/dev/null', $output, $returnCode);
        return $returnCode === 0;
    }

    private function loadRestrictions(): array
    {
        return [
            'max_execution_time' => $this->config->get('sandbox.max_execution_time', 300),
            'max_memory' => $this->config->get('sandbox.max_memory', 536870912), // 512MB
            'max_file_size' => $this->config->get('sandbox.max_file_size', 104857600), // 100MB
            'max_processes' => $this->config->get('sandbox.max_processes', 32),
            'max_open_files' => $this->config->get('sandbox.max_open_files', 256),
            'allow_network' => $this->config->get('sandbox.allow_network', false)
        ];
    }
}
