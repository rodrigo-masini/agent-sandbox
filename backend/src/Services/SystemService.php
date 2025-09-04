<?php
// ==============================================
// SYSTEM SERVICE
// ==============================================

namespace Agtsdbx\Services;

use Agtsdbx\Utils\Config;
use Agtsdbx\Utils\Logger;

class SystemService
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

    public function getHealthStatus(): array
    {
        $checks = [];
        
        // Check filesystem
        $checks['filesystem'] = $this->checkFilesystem();
        
        // Check Docker if enabled
        if ($this->config->get('docker.enabled')) {
            $checks['docker'] = $this->checkDocker();
        }
        
        // Check memory
        $checks['memory'] = $this->checkMemory();
        
        // Check disk space
        $checks['disk'] = $this->checkDiskSpace();
        
        // Overall status
        $status = 'healthy';
        foreach ($checks as $check) {
            if (!$check['healthy']) {
                $status = 'unhealthy';
                break;
            }
        }
        
        return [
            'status' => $status,
            'checks' => $checks,
            'timestamp' => date('c'),
            'version' => $this->config->get('app.version', '1.0.0')
        ];
    }

    public function getSystemInfo(): array
    {
        $info = [];
        
        // OS Information
        $info['os'] = [
            'type' => PHP_OS,
            'version' => php_uname('r'),
            'hostname' => php_uname('n'),
            'architecture' => php_uname('m')
        ];
        
        // PHP Information
        $info['php'] = [
            'version' => PHP_VERSION,
            'sapi' => PHP_SAPI,
            'extensions' => get_loaded_extensions()
        ];
        
        // System resources
        $memInfo = $this->getMemoryInfo();
        $info['memory'] = $memInfo;
        
        $diskInfo = $this->getDiskInfo();
        $info['disk'] = $diskInfo;
        
        // CPU info
        $cpuInfo = $this->getCpuInfo();
        $info['cpu'] = $cpuInfo;
        
        // Network interfaces
        $networkInfo = $this->getNetworkInfo();
        $info['network'] = $networkInfo;
        
        // Process info
        $info['process'] = [
            'pid' => getmypid(),
            'uid' => getmyuid(),
            'gid' => getmygid(),
            'user' => get_current_user()
        ];
        
        // Uptime
        $uptime = $this->executor->execute('uptime', ['timeout' => 5]);
        if ($uptime['success']) {
            $info['uptime'] = trim($uptime['stdout']);
        }
        
        return $info;
    }

    public function getMetrics(): array
    {
        return [
            'timestamp' => microtime(true),
            'memory' => [
                'current' => memory_get_usage(true),
                'peak' => memory_get_peak_usage(true),
                'limit' => $this->getMemoryLimit()
            ],
            'cpu' => $this->getCpuUsage(),
            'disk' => $this->getDiskInfo(),
            'network' => [
                'connections' => $this->getActiveConnections()
            ],
            'processes' => [
                'total' => $this->getProcessCount()
            ]
        ];
    }

    private function checkFilesystem(): array
    {
        $workdir = $this->config->get('workdir', '/app/WORKDIR');
        $healthy = is_dir($workdir) && is_writable($workdir);
        
        return [
            'healthy' => $healthy,
            'message' => $healthy ? 'Filesystem is accessible' : 'Filesystem check failed',
            'workdir' => $workdir
        ];
    }

    private function checkDocker(): array
    {
        $result = $this->executor->execute('docker version', ['timeout' => 5]);
        $healthy = $result['success'];
        
        return [
            'healthy' => $healthy,
            'message' => $healthy ? 'Docker is running' : 'Docker is not available'
        ];
    }

    private function checkMemory(): array
    {
        $memInfo = $this->getMemoryInfo();
        $usedPercent = ($memInfo['used'] / $memInfo['total']) * 100;
        $healthy = $usedPercent < 90;
        
        return [
            'healthy' => $healthy,
            'message' => sprintf('Memory usage: %.1f%%', $usedPercent),
            'used' => $memInfo['used'],
            'total' => $memInfo['total']
        ];
    }

    private function checkDiskSpace(): array
    {
        $workdir = $this->config->get('workdir', '/app/WORKDIR');
        $free = disk_free_space($workdir);
        $total = disk_total_space($workdir);
        $usedPercent = (($total - $free) / $total) * 100;
        $healthy = $usedPercent < 90;
        
        return [
            'healthy' => $healthy,
            'message' => sprintf('Disk usage: %.1f%%', $usedPercent),
            'free' => $free,
            'total' => $total
        ];
    }

    private function getMemoryInfo(): array
    {
        $result = $this->executor->execute('free -b', ['timeout' => 5]);
        
        if ($result['success']) {
            $lines = explode("\n", $result['stdout']);
            foreach ($lines as $line) {
                if (strpos($line, 'Mem:') === 0) {
                    $parts = preg_split('/\s+/', $line);
                    return [
                        'total' => (int)($parts[1] ?? 0),
                        'used' => (int)($parts[2] ?? 0),
                        'free' => (int)($parts[3] ?? 0),
                        'available' => (int)($parts[6] ?? $parts[3] ?? 0)
                    ];
                }
            }
        }
        
        // Fallback to PHP memory info
        return [
            'total' => $this->getMemoryLimit(),
            'used' => memory_get_usage(true),
            'free' => $this->getMemoryLimit() - memory_get_usage(true),
            'available' => $this->getMemoryLimit() - memory_get_usage(true)
        ];
    }

    private function getDiskInfo(): array
    {
        $workdir = $this->config->get('workdir', '/app/WORKDIR');
        
        return [
            'total' => disk_total_space($workdir),
            'free' => disk_free_space($workdir),
            'used' => disk_total_space($workdir) - disk_free_space($workdir),
            'path' => $workdir
        ];
    }

    private function getCpuInfo(): array
    {
        $result = $this->executor->execute('nproc', ['timeout' => 5]);
        $cores = $result['success'] ? (int)trim($result['stdout']) : 1;
        
        $result = $this->executor->execute('cat /proc/cpuinfo | grep "model name" | head -1', ['timeout' => 5]);
        $model = 'Unknown';
        if ($result['success']) {
            $parts = explode(':', $result['stdout']);
            $model = trim($parts[1] ?? 'Unknown');
        }
        
        return [
            'cores' => $cores,
            'model' => $model,
            'usage' => $this->getCpuUsage()
        ];
    }

    private function getCpuUsage(): float
    {
        $result = $this->executor->execute('top -bn1 | grep "Cpu(s)"', ['timeout' => 5]);
        
        if ($result['success']) {
            preg_match('/(\d+\.?\d*)\s*%?\s*id/', $result['stdout'], $matches);
            if (isset($matches[1])) {
                return 100.0 - (float)$matches[1];
            }
        }
        
        return 0.0;
    }

    private function getNetworkInfo(): array
    {
        $result = $this->executor->execute('ip addr show', ['timeout' => 5]);
        $interfaces = [];
        
        if ($result['success']) {
            $current = null;
            $lines = explode("\n", $result['stdout']);
            
            foreach ($lines as $line) {
                if (preg_match('/^\d+:\s+(\S+):/', $line, $matches)) {
                    $current = $matches[1];
                    $interfaces[$current] = [];
                } elseif ($current && preg_match('/inet\s+(\S+)/', $line, $matches)) {
                    $interfaces[$current][] = $matches[1];
                }
            }
        }
        
        return $interfaces;
    }

    private function getActiveConnections(): int
    {
        $result = $this->executor->execute('ss -tun | wc -l', ['timeout' => 5]);
        return $result['success'] ? (int)trim($result['stdout']) - 1 : 0;
    }

    private function getProcessCount(): int
    {
        $result = $this->executor->execute('ps aux | wc -l', ['timeout' => 5]);
        return $result['success'] ? (int)trim($result['stdout']) - 1 : 0;
    }

    private function getMemoryLimit(): int
    {
        $limit = ini_get('memory_limit');
        
        if ($limit == -1) {
            return PHP_INT_MAX;
        }
        
        $unit = strtolower(substr($limit, -1));
        $value = (int)substr($limit, 0, -1);
        
        switch ($unit) {
            case 'g':
                return $value * 1024 * 1024 * 1024;
            case 'm':
                return $value * 1024 * 1024;
            case 'k':
                return $value * 1024;
            default:
                return (int)$limit;
        }
    }
}
