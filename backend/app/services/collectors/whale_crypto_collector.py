import logging
from datetime import datetime, timedelta

import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

ETHERSCAN_API_URL = "https://api.etherscan.io/api"

# Known whale/exchange hot wallets to monitor
# These are public addresses of major exchanges and known large holders
WATCHED_ADDRESSES = [
    {
        "address": "0x28C6c06298d514Db089934071355E5743bf21d60",
        "label": "Binance Hot Wallet",
        "type": "exchange",
    },
    {
        "address": "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549",
        "label": "Binance Deposit",
        "type": "exchange",
    },
    {
        "address": "0xdFD5293D8e347dFe59E90eFd55b2956a1343963d",
        "label": "Coinbase Commerce",
        "type": "exchange",
    },
    {
        "address": "0xA090e606E30bD747d4E6245a1517EbE430F0057e",
        "label": "Coinbase Custody",
        "type": "exchange",
    },
    {
        "address": "0x1Db92e2EeBC8E0c075a02BeA49a2935BcD2dFCF4",
        "label": "Kraken Hot",
        "type": "exchange",
    },
    {
        "address": "0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0",
        "label": "Kraken Deposit",
        "type": "exchange",
    },
]

# Minimum transaction value in ETH to report
MIN_ETH_VALUE = 50  # ~$100k+ at typical prices


class WhaleCryptoCollector(BaseCollector):
    """Monitors large ETH transactions from known whale/exchange addresses via Etherscan."""

    SOURCE_NAME = "whale_crypto"

    async def collect(self, config: dict) -> list[dict]:
        api_key = config.get("etherscan_api_key", "")
        if not api_key:
            logger.debug("Whale Crypto: no Etherscan API key, skipping")
            return []

        items = []
        eth_price = await self._get_eth_price(api_key)

        async with httpx.AsyncClient(timeout=20) as client:
            for wallet in WATCHED_ADDRESSES:
                try:
                    # Get recent transactions
                    params = {
                        "module": "account",
                        "action": "txlist",
                        "address": wallet["address"],
                        "startblock": 0,
                        "endblock": 99999999,
                        "page": 1,
                        "offset": 20,
                        "sort": "desc",
                        "apikey": api_key,
                    }

                    resp = await client.get(ETHERSCAN_API_URL, params=params)

                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    if data.get("status") != "1":
                        continue

                    txs = data.get("result", [])

                    for tx in txs:
                        try:
                            value_wei = int(tx.get("value", "0"))
                            value_eth = value_wei / 1e18

                            if value_eth < MIN_ETH_VALUE:
                                continue

                            value_usd = value_eth * eth_price if eth_price else 0

                            # Determine direction
                            from_addr = tx.get("from", "").lower()
                            to_addr = tx.get("to", "").lower()
                            wallet_addr = wallet["address"].lower()

                            if from_addr == wallet_addr:
                                direction = "outflow"
                                # Exchange outflow = bullish (people withdrawing to hold)
                                sentiment = 0.2 if wallet["type"] == "exchange" else 0.0
                            elif to_addr == wallet_addr:
                                direction = "inflow"
                                # Exchange inflow = bearish (people depositing to sell)
                                sentiment = -0.2 if wallet["type"] == "exchange" else 0.0
                            else:
                                continue  # Neither from nor to matches

                            timestamp = int(tx.get("timeStamp", "0"))
                            tx_time = datetime.utcfromtimestamp(timestamp) if timestamp else None

                            # Skip transactions older than 24h
                            if tx_time and (datetime.utcnow() - tx_time) > timedelta(hours=24):
                                continue

                            # Relevance based on USD value
                            if value_usd > 10_000_000:
                                relevance = 0.95
                            elif value_usd > 1_000_000:
                                relevance = 0.85
                            elif value_usd > 500_000:
                                relevance = 0.7
                            else:
                                relevance = 0.55

                            tx_hash = tx.get("hash", "")

                            title = f"Whale: {value_eth:.1f} ETH (${value_usd:,.0f}) {direction} — {wallet['label']}"
                            summary = (
                                f"{'Outgoing' if direction == 'outflow' else 'Incoming'} transfer of "
                                f"{value_eth:.2f} ETH (~${value_usd:,.0f}) "
                                f"{'from' if direction == 'outflow' else 'to'} {wallet['label']}. "
                                f"{'Exchange outflow suggests accumulation.' if direction == 'outflow' and wallet['type'] == 'exchange' else ''}"
                                f"{'Exchange inflow may signal selling pressure.' if direction == 'inflow' and wallet['type'] == 'exchange' else ''}"
                            )

                            items.append(self._make_item(
                                title=title,
                                summary=summary,
                                url=f"https://etherscan.io/tx/{tx_hash}",
                                category="crypto",
                                tags=["whale", "ethereum", direction],
                                raw_relevance=relevance,
                                sentiment_score=sentiment,
                                published_at=tx_time,
                                source_id=f"eth-{tx_hash[:16]}",
                            ))

                        except (ValueError, KeyError) as e:
                            continue

                except Exception as e:
                    logger.error(f"Whale Crypto {wallet['label']} error: {type(e).__name__}")

        logger.info(f"Whale Crypto: collected {len(items)} items")
        return items

    async def _get_eth_price(self, api_key: str) -> float:
        """Get approximate ETH price in USD."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                params = {
                    "module": "stats",
                    "action": "ethprice",
                    "apikey": api_key,
                }
                resp = await client.get(ETHERSCAN_API_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "1":
                        return float(data["result"]["ethusd"])
        except Exception:
            pass
        return 3000.0  # Fallback estimate
