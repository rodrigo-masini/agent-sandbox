#!/bin/bash
# Wrapper script to handle docker-compose vs docker compose

if command -v docker-compose &> /dev/null; then
    docker-compose "$@"
elif docker compose version &> /dev/null; then
    docker compose "$@"
else
    echo "Error: Neither 'docker-compose' nor 'docker compose' found"
    exit 1
fi
