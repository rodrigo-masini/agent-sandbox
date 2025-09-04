<?php
// ==============================================
// FILE MANAGER
// ==============================================

namespace Pandora\Storage;

use Pandora\Utils\Config;

class FileManager
{
    private Config $config;
    private string $storageDir;
    private int $maxFileSize;

    public function __construct(Config $config)
    {
        $this->config = $config;
        $this->storageDir = $config->get('storage.directory', '/app/storage');
        $this->maxFileSize = $config->get('storage.max_file_size', 104857600); // 100MB
    }

    public function store(string $content, string $path = null): string
    {
        if ($path === null) {
            $path = $this->generatePath();
        }
        
        $fullPath = $this->getFullPath($path);
        $this->ensureDirectory(dirname($fullPath));
        
        if (strlen($content) > $this->maxFileSize) {
            throw new \Exception('File size exceeds maximum allowed');
        }
        
        if (file_put_contents($fullPath, $content, LOCK_EX) === false) {
            throw new \Exception('Failed to write file');
        }
        
        return $path;
    }

    public function retrieve(string $path): string
    {
        $fullPath = $this->getFullPath($path);
        
        if (!file_exists($fullPath)) {
            throw new \Exception('File not found');
        }
        
        $content = file_get_contents($fullPath);
        
        if ($content === false) {
            throw new \Exception('Failed to read file');
        }
        
        return $content;
    }

    public function delete(string $path): bool
    {
        $fullPath = $this->getFullPath($path);
        
        if (!file_exists($fullPath)) {
            return true;
        }
        
        return unlink($fullPath);
    }

    public function exists(string $path): bool
    {
        return file_exists($this->getFullPath($path));
    }

    public function size(string $path): int
    {
        $fullPath = $this->getFullPath($path);
        
        if (!file_exists($fullPath)) {
            throw new \Exception('File not found');
        }
        
        return filesize($fullPath);
    }

    public function getUrl(string $path): string
    {
        $baseUrl = $this->config->get('storage.base_url', '/storage');
        return $baseUrl . '/' . ltrim($path, '/');
    }

    private function getFullPath(string $path): string
    {
        return $this->storageDir . '/' . ltrim($path, '/');
    }

    private function ensureDirectory(string $directory): void
    {
        if (!is_dir($directory)) {
            mkdir($directory, 0755, true);
        }
    }

    private function generatePath(): string
    {
        return date('Y/m/d') . '/' . uniqid() . '.dat';
    }
}
