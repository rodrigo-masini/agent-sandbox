<?php

namespace Agtsdbx\Types;

/**
 * @phpstan-type RequestArray = array{
 *     method: string,
 *     uri: string,
 *     query: array<string, mixed>,
 *     body: string,
 *     headers: array<string, string>,
 *     ip: string,
 *     user_agent: string,
 *     timestamp: float,
 *     user?: array{id: int, username: string, role: string},
 *     params?: array<string, string>
 * }
 */
class RequestType
{
}