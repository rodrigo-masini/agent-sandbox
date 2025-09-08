    public function increment(string $key, int $value = 1, int $ttl = null): int
    {
        if ($this->redis) {
            $prefixedKey = $this->prefixKey($key);
            $result = $this->redis->incrBy($prefixedKey, $value);
            
            // FIX: Properly check the result type
            if (is_int($result)) {
                if ($ttl !== null && $result == $value) {
                    $this->redis->expire($prefixedKey, $ttl);
                }
                return $result;
            }
        }
        
        // File-based increment (not atomic)
        $current = (int)$this->get($key, 0);
        $new = $current + $value;
        $this->set($key, $new, $ttl);
        
        return $new;
    }
