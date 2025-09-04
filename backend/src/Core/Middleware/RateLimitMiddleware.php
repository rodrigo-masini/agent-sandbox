<?php

namespace Agtsdbx\Core\Middleware;

use Agtsdbx\Utils\Config;
use Agtsdbx\Storage\CacheManager;

class RateLimitMiddleware
{
    private Config $config;
    private CacheManager $cache;

    public function __construct(Config $config)
    {
        $this->config = $config;
        $this->cache = new CacheManager($config);
    }

    public function handle(array $request): array
    {
        $identifier = $this->getIdentifier($request);
        $limit = $this->config->get('rate_limit.requests_per_minute', 60);
        $window = $this->config->get('rate_limit.window_seconds', 60);
        
        $key = "rate_limit:$identifier";
        $current = $this->cache->get($key, 0);
        
        if ($current >= $limit) {
            throw new \Exception('Rate limit exceeded', 429);
        }
        
        $this->cache->increment($key, 1, $window);
        
        return $request;
    }

    private function getIdentifier(array $request): string
    {
        // Use user ID if authenticated, otherwise IP address
        if (isset($request['user']['id'])) {
            return 'user:' . $request['user']['id'];
        }
        
        return 'ip:' . $request['ip'];
    }
}
