"""Rate limiter for controlling data fetching frequency.

TODO (antirotor): This needs to be more clever, getting
    tokens from the server - permission to fetch based on
    server load.

"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Optional

from loguru import logger


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_second: float = 5.0  # Max requests per second
    burst_limit: int = 10  # Max burst requests
    cooldown_period: float = 60.0  # Cool-down after hitting limits (seconds)
    per_project_limit: float = 2.0  # Max requests per second per project


class TokenBucket:
    """Token bucket implementation for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        async with self._lock:
            now = time.time()
            time_passed = now - self.last_refill

            # Refill tokens based on time passed
            self.tokens = min(
                self.capacity,
                self.tokens + time_passed * self.refill_rate
            )
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def wait_for_tokens(
            self,
            tokens: int = 1,
            timeout: Optional[float] = None) -> bool:
        """Wait until enough tokens are available.

        Args:
            tokens: Number of tokens needed
            timeout: Maximum time to wait (seconds)

        Returns:
            True if tokens were acquired, False if timeout
        """
        start_time = time.time()

        while True:
            if await self.consume(tokens):
                return True

            if timeout and (time.time() - start_time) > timeout:
                return False

            # Wait a bit before trying again
            await asyncio.sleep(0.1)


class RateLimiter:
    """Advanced rate limiter for GraphQL requests."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter.

        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()

        # Global rate limiter
        self.global_bucket = TokenBucket(
            capacity=self.config.burst_limit,
            refill_rate=self.config.requests_per_second
        )

        # Per-project rate limiters
        self.project_buckets: dict[str, TokenBucket] = {}

        # Cool-down tracking
        self.cooldown_until: dict[str, float] = defaultdict(float)

        # Statistics
        self.stats = {
            "total_requests": 0,
            "rejected_requests": 0,
            "cooldown_activations": 0
        }

    def _get_project_bucket(self, project_name: str) -> TokenBucket:
        """Get or create token bucket for a project.

        Args:
            project_name: Name of the project

        Returns:
            Token bucket for the project
        """
        if project_name not in self.project_buckets:
            self.project_buckets[project_name] = TokenBucket(
                capacity=int(
                    self.config.per_project_limit * 2),  # Allow some burst
                refill_rate=self.config.per_project_limit
            )

        return self.project_buckets[project_name]

    async def acquire(
            self, project_name: str, timeout: Optional[float] = 30.0) -> bool:
        """Acquire permission to make a request.

        Args:
            project_name: Name of the project for per-project limiting
            timeout: Maximum time to wait for permission

        Returns:
            True if permission granted, False if denied or timeout
        """
        self.stats["total_requests"] += 1

        # Check global cool-down
        now = time.time()
        if now < self.cooldown_until["global"]:
            logger.debug("Request rejected: global cool-own active")
            self.stats["rejected_requests"] += 1
            return False

        # Check project cool-down
        if now < self.cooldown_until[project_name]:
            logger.debug(
                "Request rejected: project %s cool-down active", project_name)
            self.stats["rejected_requests"] += 1
            return False

        # Try to acquire tokens from both global and project buckets
        global_acquired = await self.global_bucket.wait_for_tokens(1, timeout)
        if not global_acquired:
            logger.debug("Request rejected: global rate limit")
            self.stats["rejected_requests"] += 1
            self._activate_cooldown("global")
            return False

        project_bucket = self._get_project_bucket(project_name)
        project_acquired = await project_bucket.wait_for_tokens(1, timeout)
        if not project_acquired:
            logger.debug(
                f"Request rejected: project {project_name} rate limit")
            self.stats["rejected_requests"] += 1
            self._activate_cooldown(project_name)
            return False

        logger.debug(f"Request approved for project {project_name}")
        return True

    def _activate_cooldown(self, key: str) -> None:
        """Activate cooldown for a key (global or project name).

        Args:
            key: Cooldown key

        """
        self.cooldown_until[key] = time.time() + self.config.cooldown_period
        self.stats["cooldown_activations"] += 1
        logger.info(
            f"Cooldown activated for {key} "
            f"for {self.config.cooldown_period} seconds")

    async def can_make_request(self, project_name: str) -> bool:
        """Check if a request can be made without acquiring tokens.

        Args:
            project_name: Name of the project

        Returns:
            True if request would be allowed
        """
        now = time.time()

        # Check cooldowns
        if now < self.cooldown_until["global"] or now < self.cooldown_until[project_name]:  # noqa: E501
            return False

        # Check if tokens are available (without consuming them)
        global_available = self.global_bucket.tokens >= 1
        project_bucket = self._get_project_bucket(project_name)
        project_available = project_bucket.tokens >= 1

        return global_available and project_available

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with statistics
        """
        now = time.time()
        active_cooldowns = {
            key: max(0, until - now)
            for key, until in self.cooldown_until.items()
            if until > now
        }

        return {
            **self.stats,
            "active_cooldowns": active_cooldowns,
            "global_tokens": self.global_bucket.tokens,
            "project_buckets": {
                name: bucket.tokens
                for name, bucket in self.project_buckets.items()
            }
        }

    def reset_cooldowns(self) -> None:
        """Reset all active cool-downs."""
        self.cooldown_until.clear()
        logger.info("All cool-downs reset")

    def update_config(self, config: RateLimitConfig) -> None:
        """Update rate limiting configuration.

        Args:
            config: New configuration
        """
        self.config = config

        # Update global bucket
        self.global_bucket.capacity = config.burst_limit
        self.global_bucket.refill_rate = config.requests_per_second

        # Update project buckets
        for bucket in self.project_buckets.values():
            bucket.capacity = int(config.per_project_limit * 2)
            bucket.refill_rate = config.per_project_limit

        logger.info("Rate limiter configuration updated")
