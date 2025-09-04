<?php
// ==============================================
// CACHE MANAGER
// ==============================================

namespace Pandora\Storage;

use Pandora\Utils\Config;

class CacheManager
{
    private Config $config;
    private $redis = null;
    private string $cacheDir;
    private int $defaultTtl;

    public function __construct(Config $config)
    {
        $this->config = $config;
        $this->cacheDir = $config->get('cache.directory', '/app/storage/cache');
        $this->defaultTtl = $config->get('cache.default_ttl', 3600);
        
        $this->initializeRedis();
        $this->ensureCacheDirectory();
    }

    public function get(string $key, $default = null)
    {
        // Try Redis first
        if ($this->redis) {
            $value = $this->redis->get($this->prefixKey($key));
            if ($value !== false) {
                return $this->unserialize($value);
            }
        }
        
        // Fallback to file cache
        $file = $this->getCacheFile($key);
        if (file_exists($file)) {
            $data = unserialize(file_get_contents($file));
            if ($data['expires'] === 0 || $data['expires'] > time()) {
                return $data['value'];
            }
            // Clean up expired file
            unlink($file);
        }
        
        return $default;
    }

    public function set(string $key, $value, int $ttl = null): bool
    {
        $ttl = $ttl ?? $this->defaultTtl;
        
        // Try Redis first
        if ($this->redis) {
            $success = $this->redis->setex(
                $this->prefixKey($key),
                $ttl,
                $this->serialize($value)
            );
            if ($success) {
                return true;
            }
        }
        
        // Fallback to file cache
        $file = $this->getCacheFile($key);
        $data = [
            'value' => $value,
            'expires' => $ttl > 0 ? time() + $ttl : 0
        ];
        
        return file_put_contents($file, serialize($data), LOCK_EX) !== false;
    }

    public function increment(string $key, int $value = 1, int $ttl = null): int
    {
        if ($this->redis) {
            $prefixedKey = $this->prefixKey($key);
            $result = $this->redis->incrBy($prefixedKey, $value);
            
            if ($ttl !== null && $result == $value) {
                $this->redis->expire($prefixedKey, $ttl);
            }
            
            return $result;
        }
        
        // File-based increment (not atomic)
        $current = $this->get($key, 0);
        $new = $current + $value;
        $this->set($key, $new, $ttl);
        
        return $new;
    }

    public function delete(string $key): bool
    {
        $success = true;
        
        if ($this->redis) {
            $success = $this->redis->del($this->prefixKey($key)) > 0;
        }
        
        $file = $this->getCacheFile($key);
        if (file_exists($file)) {
            $success = unlink($file) && $success;
        }
        
        return $success;
    }

    public function flush(): bool
    {
        $success = true;
        
        if ($this->redis) {
            $success = $this->redis->flushDB();
        }
        
        // Clear file cache
        $files = glob($this->cacheDir . '/*.cache');
        foreach ($files as $file) {
            unlink($file);
        }
        
        return $success;
    }

    private function initializeRedis(): void
    {
        if (!extension_loaded('redis')) {
            return;
        }
        
        $host = $this->config->get('redis.host', 'localhost');
        $port = $this->config->get('redis.port', 6379);
        $password = $this->config->get('redis.password');
        $database = $this->config->get('redis.database', 0);
        
        try {
            $this->redis = new \Redis();
            $this->redis->connect($host, $port, 2.0);
            
            if ($password) {
                $this->redis->auth($password);
            }
            
            $this->redis->select($database);
            
        } catch (\Exception $e) {
            // Log error and fall back to file cache
            error_log('Redis connection failed: ' . $e->getMessage());
            $this->redis = null;
        }
    }

    private function ensureCacheDirectory(): void
    {
        if (!is_dir($this->cacheDir)) {
            mkdir($this->cacheDir, 0755, true);
        }
    }

    private function prefixKey(string $key): string
    {
        $prefix = $this->config->get('cache.prefix', 'pandora');
        return $prefix . ':' . $key;
    }

    private function getCacheFile(string $key): string
    {
        return $this->cacheDir . '/' . md5($key) . '.cache';
    }

    private function serialize($value): string
    {
        return serialize($value);
    }

    private function unserialize(string $value)
    {
        return unserialize($value);
    }
}
