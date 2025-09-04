<?php
// ==============================================
// DATABASE SERVICE
// ==============================================

namespace Pandora\Services;

use Pandora\Utils\Config;
use Pandora\Utils\Logger;
use PDO;
use PDOException;

class DatabaseService
{
    private Config $config;
    private Logger $logger;
    private array $connections = [];

    public function __construct(Config $config, Logger $logger)
    {
        $this->config = $config;
        $this->logger = $logger;
    }

    public function query(string $sql, array $params = [], string $database = 'default'): array
    {
        $pdo = $this->getConnection($database);
        
        try {
            $stmt = $pdo->prepare($sql);
            $stmt->execute($params);
            
            $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            return [
                'success' => true,
                'data' => $results,
                'rowCount' => $stmt->rowCount()
            ];
            
        } catch (PDOException $e) {
            $this->logger->error('Database query failed', [
                'error' => $e->getMessage(),
                'sql' => $sql
            ]);
            throw new \Exception('Query failed: ' . $e->getMessage());
        }
    }

    public function execute(string $sql, array $params = [], string $database = 'default'): array
    {
        $pdo = $this->getConnection($database);
        
        try {
            $pdo->beginTransaction();
            
            $stmt = $pdo->prepare($sql);
            $stmt->execute($params);
            
            $rowCount = $stmt->rowCount();
            $lastInsertId = null;
            
            if (stripos($sql, 'INSERT') === 0) {
                $lastInsertId = $pdo->lastInsertId();
            }
            
            $pdo->commit();
            
            return [
                'success' => true,
                'rowCount' => $rowCount,
                'lastInsertId' => $lastInsertId
            ];
            
        } catch (PDOException $e) {
            $pdo->rollBack();
            
            $this->logger->error('Database execute failed', [
                'error' => $e->getMessage(),
                'sql' => $sql
            ]);
            
            throw new \Exception('Execute failed: ' . $e->getMessage());
        }
    }

    private function getConnection(string $database = 'default'): PDO
    {
        if (isset($this->connections[$database])) {
            return $this->connections[$database];
        }
        
        $dsn = $this->config->get("database.$database.dsn");
        if (!$dsn) {
            // Use DATABASE_URL environment variable as fallback
            $databaseUrl = $_ENV['DATABASE_URL'] ?? '';
            if ($databaseUrl) {
                $dsn = $this->parseDatabaseUrl($databaseUrl);
            } else {
                throw new \Exception("Database configuration not found for: $database");
            }
        }
        
        $username = $this->config->get("database.$database.username", '');
        $password = $this->config->get("database.$database.password", '');
        $options = $this->config->get("database.$database.options", [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false
        ]);
        
        try {
            $pdo = new PDO($dsn, $username, $password, $options);
            $this->connections[$database] = $pdo;
            return $pdo;
            
        } catch (PDOException $e) {
            $this->logger->error('Database connection failed', [
                'database' => $database,
                'error' => $e->getMessage()
            ]);
            throw new \Exception('Database connection failed');
        }
    }

    private function parseDatabaseUrl(string $url): string
    {
        $parts = parse_url($url);
        
        if (!$parts) {
            throw new \Exception('Invalid database URL');
        }
        
        $scheme = $parts['scheme'] ?? '';
        $host = $parts['host'] ?? '';
        $port = $parts['port'] ?? '';
        $user = $parts['user'] ?? '';
        $pass = $parts['pass'] ?? '';
        $path = ltrim($parts['path'] ?? '', '/');
        
        switch ($scheme) {
            case 'mysql':
                $dsn = "mysql:host=$host";
                if ($port) $dsn .= ";port=$port";
                if ($path) $dsn .= ";dbname=$path";
                break;
                
            case 'pgsql':
            case 'postgresql':
                $dsn = "pgsql:host=$host";
                if ($port) $dsn .= ";port=$port";
                if ($path) $dsn .= ";dbname=$path";
                break;
                
            case 'sqlite':
                $dsn = "sqlite:$path";
                break;
                
            default:
                throw new \Exception("Unsupported database scheme: $scheme");
        }
        
        return $dsn;
    }
}
