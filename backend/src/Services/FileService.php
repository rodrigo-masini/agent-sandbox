<?php
// ==============================================
// FILE SERVICE
// ==============================================

namespace Agtsdbx\Services;

use Agtsdbx\Utils\Config;
use Agtsdbx\Utils\Logger;
use Agtsdbx\Storage\FileManager;

class FileService
{
    private Config $config;
    private Logger $logger;
    private FileManager $fileManager; // This type hint is now correct
    private string $workdir;

    public function __construct(Config $config, Logger $logger)
    {
        $this->config = $config;
        $this->logger = $logger;
        $this->fileManager = new FileManager($config); // This instantiation is now correct
        $this->workdir = $config->get('workdir', '/app/WORKDIR');
    }

    public function write(string $filePath, string $content, array $options = []): array
    {
        $append = $options['append'] ?? false;
        $createDirs = $options['create_dirs'] ?? true;
        
        // Resolve path
        $absolutePath = $this->resolvePath($filePath);
        
        // Create directory if needed
        if ($createDirs) {
            $dir = dirname($absolutePath);
            if (!is_dir($dir)) {
                mkdir($dir, 0755, true);
            }
        }
        
        // Write file
        $flags = $append ? FILE_APPEND : 0;
        $result = file_put_contents($absolutePath, $content, $flags);
        
        if ($result === false) {
            throw new \Exception('Failed to write file');
        }
        
        return [
            'success' => true,
            'path' => $filePath,
            'size' => strlen($content),
            'absolute_path' => $absolutePath
        ];
    }

    public function read(string $filePath, array $options = []): array
    {
        $encoding = $options['encoding'] ?? 'utf-8';
        $maxSize = $options['max_size'] ?? $this->config->get('filesystem.max_file_size', 10485760);
        
        // Resolve path
        $absolutePath = $this->resolvePath($filePath);
        
        if (!file_exists($absolutePath)) {
            throw new \Exception('File not found', 404);
        }
        
        if (!is_readable($absolutePath)) {
            throw new \Exception('File not readable', 403);
        }
        
        $size = filesize($absolutePath);
        if ($size > $maxSize) {
            throw new \Exception("File too large: $size bytes", 413);
        }
        
        $content = file_get_contents($absolutePath);
        
        if ($content === false) {
            throw new \Exception('Failed to read file');
        }
        
        // Convert encoding if needed
        if ($encoding !== 'utf-8') {
            $content = mb_convert_encoding($content, 'utf-8', $encoding);
        }
        
        return [
            'success' => true,
            'content' => $content,
            'size' => $size,
            'path' => $filePath,
            'mime_type' => mime_content_type($absolutePath)
        ];
    }

    public function list(string $path = '.', array $options = []): array
    {
        $recursive = $options['recursive'] ?? false;
        $pattern = $options['pattern'] ?? '*';
        $showHidden = $options['show_hidden'] ?? false;
        $sort = $options['sort'] ?? 'name';
        
        // Resolve path
        $absolutePath = $this->resolvePath($path);
        
        if (!is_dir($absolutePath)) {
            throw new \Exception('Directory not found', 404);
        }
        
        $files = [];
        
        if ($recursive) {
            $iterator = new \RecursiveIteratorIterator(
                new \RecursiveDirectoryIterator($absolutePath, \FilesystemIterator::SKIP_DOTS),
                \RecursiveIteratorIterator::SELF_FIRST
            );
        } else {
            $iterator = new \DirectoryIterator($absolutePath);
        }
        
        foreach ($iterator as $fileInfo) {
            $filename = $fileInfo->getFilename();
            
            // Skip hidden files if not requested
            if (!$showHidden && $filename[0] === '.') {
                continue;
            }
            
            // Check pattern
            if ($pattern !== '*' && !fnmatch($pattern, $filename)) {
                continue;
            }
            
            $relativePath = str_replace($absolutePath . '/', '', $fileInfo->getPathname());
            
            $files[] = [
                'name' => $filename,
                'path' => $relativePath,
                'type' => $fileInfo->isDir() ? 'directory' : 'file',
                'size' => $fileInfo->isFile() ? $fileInfo->getSize() : 0,
                'modified' => $fileInfo->getMTime(),
                'permissions' => substr(sprintf('%o', $fileInfo->getPerms()), -4)
            ];
        }
        
        // Sort files
        $this->sortFiles($files, $sort);
        
        return [
            'success' => true,
            'path' => $path,
            'files' => $files,
            'count' => count($files)
        ];
    }

    public function delete(string $filePath): array
    {
        // Resolve path
        $absolutePath = $this->resolvePath($filePath);
        
        if (!file_exists($absolutePath)) {
            throw new \Exception('File not found', 404);
        }
        
        if (is_dir($absolutePath)) {
            // Delete directory
            if (!$this->deleteDirectory($absolutePath)) {
                throw new \Exception('Failed to delete directory');
            }
        } else {
            // Delete file
            if (!unlink($absolutePath)) {
                throw new \Exception('Failed to delete file');
            }
        }
        
        return [
            'success' => true,
            'path' => $filePath,
            'deleted' => true
        ];
    }

    private function resolvePath(string $path): string
    {
        // If absolute path, use it; otherwise, relative to workdir
        if ($path[0] === '/') {
            $absolutePath = $path;
        } else {
            $absolutePath = $this->workdir . '/' . $path;
        }
        
        // Resolve .. and . in path
        $absolutePath = realpath($absolutePath) ?: $absolutePath;
        
        // Ensure path is within allowed directories
        $allowed = false;
        foreach ($this->config->get('filesystem.allowed_paths', []) as $allowedPath) {
            if (strpos($absolutePath, realpath($allowedPath)) === 0) {
                $allowed = true;
                break;
            }
        }
        
        if (!$allowed) {
            throw new \Exception('Path not allowed', 403);
        }
        
        return $absolutePath;
    }

    private function deleteDirectory(string $dir): bool
    {
        if (!is_dir($dir)) {
            return false;
        }
        
        $files = array_diff(scandir($dir), ['.', '..']);
        
        foreach ($files as $file) {
            $path = $dir . '/' . $file;
            if (is_dir($path)) {
                $this->deleteDirectory($path);
            } else {
                unlink($path);
            }
        }
        
        return rmdir($dir);
    }

    private function sortFiles(array &$files, string $sort): void
    {
        switch ($sort) {
            case 'name':
                usort($files, fn($a, $b) => strcmp($a['name'], $b['name']));
                break;
            case 'size':
                usort($files, fn($a, $b) => $b['size'] - $a['size']);
                break;
            case 'modified':
                usort($files, fn($a, $b) => $b['modified'] - $a['modified']);
                break;
            case 'type':
                usort($files, fn($a, $b) => strcmp($a['type'], $b['type']));
                break;
        }
    }
}
