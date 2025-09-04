<?php
// ==============================================
// NETWORK SERVICE
// ==============================================

namespace Agtsdbx\Services;

use Agtsdbx\Utils\Config;
use Agtsdbx\Utils\Logger;

class NetworkService
{
    private Config $config;
    private Logger $logger;
    private int $maxRequestSize;
    private int $timeout;

    public function __construct(Config $config, Logger $logger)
    {
        $this->config = $config;
        $this->logger = $logger;
        $this->maxRequestSize = $config->get('network.max_request_size', 1048576);
        $this->timeout = $config->get('network.timeout', 30);
    }

    public function makeRequest(
        string $url, 
        string $method = 'GET', 
        array $headers = [], 
        $body = null, 
        array $options = []
    ): array {
        $timeout = $options['timeout'] ?? $this->timeout;
        
        // Initialize cURL
        $ch = curl_init();
        
        // Set basic options
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, min(10, $timeout));
        curl_setopt($ch, CURLOPT_MAXREDIRS, 5);
        
        // Set method
        switch (strtoupper($method)) {
            case 'POST':
                curl_setopt($ch, CURLOPT_POST, true);
                break;
            case 'PUT':
                curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PUT');
                break;
            case 'DELETE':
                curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
                break;
            case 'PATCH':
                curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PATCH');
                break;
            case 'HEAD':
                curl_setopt($ch, CURLOPT_NOBODY, true);
                break;
        }
        
        // Set body if provided
        if ($body !== null) {
            if (is_array($body) || is_object($body)) {
                $body = json_encode($body);
                $headers['Content-Type'] = 'application/json';
            }
            
            if (strlen($body) > $this->maxRequestSize) {
                throw new \Exception('Request body too large', 413);
            }
            
            curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        }
        
        // Set headers
        $headerArray = [];
        foreach ($headers as $key => $value) {
            $headerArray[] = "$key: $value";
        }
        if (!empty($headerArray)) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headerArray);
        }
        
        // Capture response headers
        $responseHeaders = [];
        curl_setopt($ch, CURLOPT_HEADERFUNCTION, function($ch, $header) use (&$responseHeaders) {
            $len = strlen($header);
            $header = explode(':', $header, 2);
            if (count($header) < 2) return $len;
            
            $responseHeaders[strtolower(trim($header[0]))] = trim($header[1]);
            return $len;
        });
        
        // Execute request
        $startTime = microtime(true);
        $response = curl_exec($ch);
        $duration = microtime(true) - $startTime;
        
        // Check for errors
        if ($response === false) {
            $error = curl_error($ch);
            curl_close($ch);
            throw new \Exception("Network request failed: $error");
        }
        
        // Get info
        $info = curl_getinfo($ch);
        curl_close($ch);
        
        return [
            'success' => true,
            'data' => [
                'status_code' => $info['http_code'],
                'body' => $response,
                'headers' => $responseHeaders,
                'info' => [
                    'url' => $info['url'],
                    'content_type' => $info['content_type'],
                    'size' => $info['size_download'],
                    'time' => $duration
                ]
            ]
        ];
    }

    public function downloadFile(string $url, string $outputPath, array $options = []): array
    {
        $timeout = $options['timeout'] ?? 300;
        $maxSize = $options['max_size'] ?? 104857600; // 100MB default
        
        // Ensure output directory exists
        $dir = dirname($outputPath);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        
        // Open file for writing
        $fp = fopen($outputPath, 'w+');
        if (!$fp) {
            throw new \Exception('Cannot open output file for writing');
        }
        
        // Initialize cURL
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_FILE, $fp);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, min(30, $timeout));
        curl_setopt($ch, CURLOPT_MAXREDIRS, 5);
        
        // Progress callback to check file size
        $downloadedSize = 0;
        curl_setopt($ch, CURLOPT_PROGRESSFUNCTION, function($ch, $dlTotal, $dlNow, $ulTotal, $ulNow) use ($maxSize, &$downloadedSize) {
            $downloadedSize = $dlNow;
            if ($dlNow > $maxSize) {
                return 1; // Abort transfer
            }
            return 0;
        });
        curl_setopt($ch, CURLOPT_NOPROGRESS, false);
        
        // Execute download
        $startTime = microtime(true);
        $success = curl_exec($ch);
        $duration = microtime(true) - $startTime;
        
        // Get info
        $info = curl_getinfo($ch);
        $error = curl_error($ch);
        
        curl_close($ch);
        fclose($fp);
        
        if (!$success) {
            // Clean up failed download
            if (file_exists($outputPath)) {
                unlink($outputPath);
            }
            
            if ($downloadedSize > $maxSize) {
                throw new \Exception("File too large: exceeds maximum size of $maxSize bytes");
            }
            
            throw new \Exception("Download failed: $error");
        }
        
        return [
            'success' => true,
            'path' => $outputPath,
            'size' => filesize($outputPath),
            'url' => $url,
            'duration' => $duration,
            'content_type' => $info['content_type']
        ];
    }
}
