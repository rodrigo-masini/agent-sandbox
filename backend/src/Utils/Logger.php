<?php
// ==============================================
// LOGGER IMPLEMENTATION
// ==============================================

namespace Pandora\Utils;

use Psr\Log\LoggerInterface;
use Psr\Log\LogLevel;

class Logger implements LoggerInterface
{
    private Config $config;
    private string $logPath;
    private string $logLevel;

    public function __construct(Config $config)
    {
        $this->config = $config;
        $this->logPath = $config->get('logging.path', '/app/storage/logs/app.log');
        $this->logLevel = $config->get('logging.level', LogLevel::INFO);
    }

    public function emergency($message, array $context = []): void
    {
        $this->log(LogLevel::EMERGENCY, $message, $context);
    }

    public function alert($message, array $context = []): void
    {
        $this->log(LogLevel::ALERT, $message, $context);
    }

    public function critical($message, array $context = []): void
    {
        $this->log(LogLevel::CRITICAL, $message, $context);
    }

    public function error($message, array $context = []): void
    {
        $this->log(LogLevel::ERROR, $message, $context);
    }

    public function warning($message, array $context = []): void
    {
        $this->log(LogLevel::WARNING, $message, $context);
    }

    public function notice($message, array $context = []): void
    {
        $this->log(LogLevel::NOTICE, $message, $context);
    }

    public function info($message, array $context = []): void
    {
        $this->log(LogLevel::INFO, $message, $context);
    }

    public function debug($message, array $context = []): void
    {
        $this->log(LogLevel::DEBUG, $message, $context);
    }

    public function log($level, $message, array $context = []): void
    {
        // Check if we should log this level
        if (!$this->shouldLog($level)) {
            return;
        }

        $logEntry = [
            'timestamp' => date('c'),
            'level' => $level,
            'message' => $message,
            'context' => $context
        ];

        // Format log message
        $formattedMessage = sprintf(
            "[%s] %s: %s %s\n",
            $logEntry['timestamp'],
            strtoupper($logEntry['level']),
            $logEntry['message'],
            empty($context) ? '' : json_encode($context)
        );

        // Write to file
        $this->writeToFile($formattedMessage);

        // Also output to stderr for ERROR and above
        if (in_array($level, [LogLevel::EMERGENCY, LogLevel::ALERT, LogLevel::CRITICAL, LogLevel::ERROR])) {
            error_log($formattedMessage);
        }
    }

    private function shouldLog(string $level): bool
    {
        $levels = [
            LogLevel::DEBUG => 0,
            LogLevel::INFO => 1,
            LogLevel::NOTICE => 2,
            LogLevel::WARNING => 3,
            LogLevel::ERROR => 4,
            LogLevel::CRITICAL => 5,
            LogLevel::ALERT => 6,
            LogLevel::EMERGENCY => 7
        ];

        $currentLevel = $levels[$this->logLevel] ?? 1;
        $messageLevel = $levels[$level] ?? 0;

        return $messageLevel >= $currentLevel;
    }

    private function writeToFile(string $message): void
    {
        $dir = dirname($this->logPath);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }

        file_put_contents($this->logPath, $message, FILE_APPEND | LOCK_EX);
    }
}
