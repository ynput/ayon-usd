# Caching Setup

This document describes how caching works in the AYON USD addon and how to set it up using the implementation in [client/ayon_usd/cache_manager](client/ayon_usd/cache_manager).

## Overview

The cache system is started by the addon tray service and uses:

- `CacheService` for lifecycle, prefetching, and invalidation handling.
- `MemcachedClient` for storing path lookups in memcached.
- `WebSocketClient` for invalidating stale keys when entities change.
- `RateLimiter` to avoid overloading server requests.

If memcached is unavailable, the service falls back to `NullCacheClient` (caching effectively disabled).

Relevant sources:

- [client/ayon_usd/cache_manager/cache_service.py](client/ayon_usd/cache_manager/cache_service.py)
- [client/ayon_usd/cache_manager/memcached_client.py](client/ayon_usd/cache_manager/memcached_client.py)
- [client/ayon_usd/addon.py](client/ayon_usd/addon.py)
- [client/ayon_usd/hooks/pre_resolver_init.py](client/ayon_usd/hooks/pre_resolver_init.py)
- [server/settings/main.py](server/settings/main.py)

## Prerequisites

1. AYON USD addon installed and enabled.
2. AYON client runtime has required dependencies (includes `pymemcache`).
3. At least one reachable memcached server.


## Configure Memcached In AYON Settings

In AYON Studio Settings:

1. Go to USD addon settings.
2. Open **Memcached Support Config**.
3. Enable **Enable Memcached**.
4. Set **Memcached Servers** to one or more `host:port` entries.

This configuration maps to `settings["usd"]["memcached"]` in code and is used by both the tray cache service and launch hook environment setup.

## Runtime Environment Overrides

The following environment variables are supported by the client-side cache setup:

- `AYON_MEMCACHED_SERVERS`
: Comma-separated memcached endpoints. Overrides server settings when set.
- `AYON_DEFAULT_TTL`
: Default key TTL in seconds. Default: `3600`.
- `AYON_PREFETCH_INTERVAL`
: Prefetch loop interval in seconds. Default: `300`.
- `AYON_MAX_CONCURRENT`
: Max concurrent prefetch tasks. Default: `5`.
- `AYON_RATE_LIMIT_RPS`
: Global request rate. Default: `5.0`.
- `AYON_BURST_LIMIT`
: Allowed burst size. Default: `10`.
- `AYON_COOLDOWN_PERIOD`
: Cooldown window in seconds. Default: `60.0`.
- `AYON_PROJECT_RATE_LIMIT`
: Per-project request rate. Default: `2.0`.
- `AYON_PRECACHE_PROJECTS`
: Comma-separated project list to prefetch.
- `AYON_PRECACHE_FOLDERS_<PROJECT>`
: Optional comma-separated folder list per project.

Launch-time resolver environment:

- `AYON_MEMCACHED_ENABLED=true`
- `AYON_MEMCACHED_SERVERS=<comma-separated hosts>`

Those are injected by the pre-launch hook when memcached is enabled in settings.

## Memcached Setup By Platform

Use one or more memcached servers listening on TCP port `11211` (or your custom port).

***Note:** You can use rust-based alternative that should be fully compatible with memcached (https://memc.rs/)*

### Windows

Official memcached does not provide a native Windows service build. Recommended options:

1. Run memcached in Docker Desktop.
2. Use WSL2 and run the Linux package there.
3. Find Windows build on the internet like https://github.com/jefyt/memcached-windows
4. Build your own


Docker example:

```powershell
docker run --name ayon-memcached -p 11211:11211 -d memcached:1.6-alpine
```

Validate from PowerShell:

```powershell
docker logs ayon-memcached
```

If the AYON process runs on Windows host, use `localhost:11211`.

### Linux

Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y memcached
sudo systemctl enable --now memcached
```

RHEL/CentOS/Fedora:

```bash
sudo dnf install -y memcached
sudo systemctl enable --now memcached
```

Optional quick check:

```bash
echo stats | nc 127.0.0.1 11211
```

### macOS

Homebrew setup:

```bash
brew install memcached
brew services start memcached
```

Quick check:

```bash
echo stats | nc 127.0.0.1 11211
```

## Single Server vs Multiple Servers

Set multiple servers as:

```text
AYON_MEMCACHED_SERVERS=cache-1:11211,cache-2:11211,cache-3:11211
```

## Recommended Initial Configuration

Start with:

- one local memcached server
- `AYON_DEFAULT_TTL=3600`
- `AYON_PREFETCH_INTERVAL=300`
- `AYON_PRECACHE_PROJECTS=<active projects only>`

Then monitor logs and adjust interval/rate limit to match your server capacity.

## Troubleshooting

### Cache service does not start

Check:

- Memcached host/port is reachable from the AYON client process.
- Memcached is enabled in USD addon settings.

### Caching seems disabled

The service will fall back to `NullCacheClient` when memcached initialization fails. Check client logs for messages similar to:

- `Failed to initialize Memcached client`
- `Using NullCacheClient, caching is disabled`

### No prefetched data

Check:

- `AYON_PRECACHE_PROJECTS` contains valid project names.
- API key has permission to query assigned paths.
- Rate limiting is not too restrictive.

## Notes

- Memcached content is ephemeral by design.
- Choose TTL and prefetch frequency based on expected project churn.
- Prefer local network memcached instances with low latency to client hosts.