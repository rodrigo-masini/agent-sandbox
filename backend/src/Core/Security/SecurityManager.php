<?php

namespace Agtsdbx\Core\Security;

use Agtsdbx\Utils\Config;
use Agtsdbx\Utils\Logger;

class SecurityManager
{
    private Config $config;
    private Logger $logger;
    private array $securityConfig;

    public function __construct(Config $config, Logger $logger = null)
    {
        $this->config = $config;
        $this->logger = $logger ?? new Logger($config);
        $this->securityConfig = $config->get('security', []);
    }

    public function isCommandAllowed(string $command): bool
    {
        // Check command length
        if (strlen($command) > $this->securityConfig['commands']['max_length']) {
            $this->logger->warning('Command rejected: too long', ['command' => substr($command, 0, 100) . '...']);
            return false;
        }

        // Check whitelist if enabled
        if ($this->securityConfig['commands']['whitelist_enabled']) {
            $allowed = false;
            foreach ($this->securityConfig['commands']['whitelist'] as $pattern) {
                if (strpos($command, $pattern) === 0) {
                    $allowed = true;
                    break;
                }
            }
            if (!$allowed) {
                $this->logger->warning('Command rejected: not in whitelist', ['command' => $command]);
                return false;
            }
        }

        // Check blacklist if enabled
        if ($this->securityConfig['commands']['blacklist_enabled']) {
            foreach ($this->securityConfig['commands']['blacklist'] as $pattern) {
                if (strpos($command, $pattern) !== false) {
                    $this->logger->warning('Command rejected: matches blacklist', [
                        'command' => $command,
                        'pattern' => $pattern
                    ]);
                    return false;
                }
            }
        }

        // Check for dangerous patterns
        $dangerousPatterns = [
            '/\|\s*sh\s*$/',
            '/\|\s*bash\s*$/',
            '/\$\(.*\)/',
            '/`.*`/',
            '/;\s*(rm|del|format)/',
            '/>\s*\/dev\/(null|zero|random|urandom)/',
            '/\|\s*nc\s+/',
            '/\|\s*netcat\s+/',
        ];

        foreach ($dangerousPatterns as $pattern) {
            if (preg_match($pattern, $command)) {
                $this->logger->warning('Command rejected: dangerous pattern', [
                    'command' => $command,
                    'pattern' => $pattern
                ]);
                return false;
            }
        }

        return true;
    }

    public function sanitizeCommand(string $command): string
    {
        // Remove null bytes
        $command = str_replace("\0", '', $command);
        
        // Remove control characters except newline and tab
        $command = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/', '', $command);
        
        // Trim whitespace
        $command = trim($command);
        
        return $command;
    }

    public function isPathAllowed(string $path): bool
    {
        // Resolve path to prevent directory traversal
        $realPath = realpath($path);
        if ($realPath === false) {
            // Path doesn't exist, check if parent directory is allowed
            $realPath = realpath(dirname($path));
            if ($realPath === false) {
                return false;
            }
            $realPath = $realPath . '/' . basename($path);
        }

        // Check against forbidden paths
        foreach ($this->securityConfig['filesystem']['forbidden_paths'] as $forbidden) {
            if (strpos($realPath, $forbidden) === 0) {
                $this->logger->warning('Path rejected: forbidden', ['path' => $path, 'real_path' => $realPath]);
                return false;
            }
        }

        // Check against allowed paths
        $allowed = false;
        foreach ($this->securityConfig['filesystem']['allowed_paths'] as $allowedPath) {
            if (strpos($realPath, realpath($allowedPath)) === 0) {
                $allowed = true;
                break;
            }
        }

        if (!$allowed) {
            $this->logger->warning('Path rejected: not in allowed paths', ['path' => $path, 'real_path' => $realPath]);
            return false;
        }

        return true;
    }

    public function validateFileExtension(string $filename): bool
    {
        $extension = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
        $allowed = $this->securityConfig['filesystem']['allowed_extensions'];
        
        if (!in_array($extension, $allowed)) {
            $this->logger->warning('File rejected: extension not allowed', [
                'filename' => $filename,
                'extension' => $extension
            ]);
            return false;
        }

        return true;
    }

    public function validateFileSize(int $size): bool
    {
        $maxSize = $this->securityConfig['filesystem']['max_file_size'];
        
        if ($size > $maxSize) {
            $this->logger->warning('File rejected: too large', [
                'size' => $size,
                'max_size' => $maxSize
            ]);
            return false;
        }

        return true;
    }

    public function isNetworkRequestAllowed(string $url): bool
    {
        $parsedUrl = parse_url($url);
        
        if (!$parsedUrl || !isset($parsedUrl['host'])) {
            return false;
        }

        $host = $parsedUrl['host'];

        // Check against blocked IPs
        foreach ($this->securityConfig['network']['blocked_ips'] as $blockedIp) {
            if ($this->ipInRange($host, $blockedIp)) {
                $this->logger->warning('Network request rejected: blocked IP', ['url' => $url, 'host' => $host]);
                return false;
            }
        }

        // Check against allowed domains
        $allowedDomains = $this->securityConfig['network']['allowed_domains'];
        if (!empty($allowedDomains)) {
            $allowed = false;
            foreach ($allowedDomains as $domain) {
                if ($host === $domain || str_ends_with($host, '.' . $domain)) {
                    $allowed = true;
                    break;
                }
            }
            if (!$allowed) {
                $this->logger->warning('Network request rejected: domain not allowed', ['url' => $url, 'host' => $host]);
                return false;
            }
        }

        return true;
    }

    public function encryptSensitiveData(string $data): string
    {
        $key = $this->securityConfig['encryption']['key'];
        $algorithm = $this->securityConfig['encryption']['algorithm'];
        
        $iv = random_bytes(16);
        $encrypted = openssl_encrypt($data, $algorithm, $key, 0, $iv);
        
        return base64_encode($iv . $encrypted);
    }

    public function decryptSensitiveData(string $encryptedData): string
    {
        $key = $this->securityConfig['encryption']['key'];
        $algorithm = $this->securityConfig['encryption']['algorithm'];
        
        $data = base64_decode($encryptedData);
        $iv = substr($data, 0, 16);
        $encrypted = substr($data, 16);
        
        return openssl_decrypt($encrypted, $algorithm, $key, 0, $iv);
    }

    public function redactSensitiveInfo(string $text): string
    {
        $patterns = $this->securityConfig['logging']['sensitive_patterns'];
        
        foreach ($patterns as $pattern) {
            $text = preg_replace($pattern . '\s*[=:]\s*\S+', '$0 [REDACTED]', $text);
        }
        
        return $text;
    }

    private function ipInRange(string $ip, string $range): bool
    {
        if (strpos($range, '/') === false) {
            return $ip === $range;
        }

        list($subnet, $bits) = explode('/', $range);
        
        if (!filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) || 
            !filter_var($subnet, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4)) {
            return false;
        }

        $ip = ip2long($ip);
        $subnet = ip2long($subnet);
        $mask = -1 << (32 - $bits);
        
        return ($ip & $mask) === ($subnet & $mask);
    }
}
