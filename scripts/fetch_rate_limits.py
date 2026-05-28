"""Fetch and display actual rate limits and endpoint costs from Kalshi.

Run with: uv run python scripts/fetch_rate_limits.py
Requires: .env with KALSHI_PROD_API_KEY_ID and KALSHI_PROD_PRIVATE_KEY_FILE
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

from pykalshi.auth import KalshiCredentials
from pykalshi.config import ClientConfig, Environment
from pykalshi.http_client import KalshiHttpClient

load_dotenv()

KEY_ID = os.environ.get("KALSHI_PROD_API_KEY_ID", "")
KEY_FILE = os.environ.get("KALSHI_PROD_PRIVATE_KEY_FILE", "")


async def main() -> None:
    if not KEY_ID or not KEY_FILE:
        print("ERROR: Set KALSHI_PROD_API_KEY_ID and KALSHI_PROD_PRIVATE_KEY_FILE in .env")
        sys.exit(1)

    creds = KalshiCredentials.from_key_file(KEY_ID, KEY_FILE)
    config = ClientConfig(environment=Environment.PROD)

    async with KalshiHttpClient(creds, config) as client:
        # Fetch rate limits
        limits = await client.get_api_limits()
        print("=" * 60)
        print("ACCOUNT API LIMITS")
        print("=" * 60)
        print(f"  Usage tier:      {limits.usage_tier}")
        print()
        print("  Read bucket:")
        print(f"    refill_rate:    {limits.read.refill_rate} tokens/sec")
        print(f"    bucket_capacity:{limits.read.bucket_capacity} tokens")
        print()
        print("  Write bucket:")
        print(f"    refill_rate:    {limits.write.refill_rate} tokens/sec")
        print(f"    bucket_capacity:{limits.write.bucket_capacity} tokens")
        print()
        print("  pykalshi defaults (for comparison):")
        print(f"    read_rate:      {config.read_rate} (used as both rate and capacity)")
        print(f"    write_rate:     {config.write_rate} (used as both rate and capacity)")
        print()

        # Fetch endpoint costs
        costs = await client.get_endpoint_costs()
        print("=" * 60)
        print("ENDPOINT COSTS")
        print("=" * 60)
        print(f"  Default cost:    {costs.default_cost} tokens")
        print(f"  pykalshi default: 1.0 (hardcoded for all endpoints)")
        print()

        if costs.endpoint_costs:
            print(f"  Non-default endpoints ({len(costs.endpoint_costs)}):")
            print(f"  {'METHOD':<8} {'COST':>6}  PATH")
            print(f"  {'-'*8} {'-'*6}  {'-'*40}")
            for ec in sorted(costs.endpoint_costs, key=lambda e: (e.path, e.method)):
                print(f"  {ec.method:<8} {ec.cost:>6}  {ec.path}")
        else:
            print("  No non-default endpoint costs (all endpoints use default cost)")


if __name__ == "__main__":
    asyncio.run(main())
