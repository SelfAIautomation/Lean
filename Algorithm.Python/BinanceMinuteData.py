# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Simple helper script to fetch 1-minute BTCUSDT data from Binance.
The script queries Binance's public REST API every minute and prints the
latest open, high, low, close and volume values.
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Dict


def fetch_latest_kline(symbol: str = "BTCUSDT") -> Dict[str, Any] | None:
    """Fetch the latest kline for the given symbol from Binance."""
    url = (
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=1"
    )
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode("utf-8"))

    if not data:
        return None

    k = data[0]
    return {
        "open_time": k[0],
        "open": float(k[1]),
        "high": float(k[2]),
        "low": float(k[3]),
        "close": float(k[4]),
        "volume": float(k[5]),
        "close_time": k[6],
    }


def main() -> None:
    """Continuously fetch and display the latest BTCUSDT minute kline."""
    while True:
        kline = fetch_latest_kline()
        if kline is not None:
            print(
                f"Time: {kline['open_time']} Open: {kline['open']} Close: {kline['close']} Volume: {kline['volume']}"
            )
        else:
            print("No data returned from Binance")
        time.sleep(60)


if __name__ == "__main__":
    main()
