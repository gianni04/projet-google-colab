"""
amm.py — Constant-product market-microstructure model for the HLD/ETH pool.

The active liquidity of a Uniswap V4 range behaves locally as a constant-product
market maker (CPMM) with invariant x * y = k. We use the deployed reserves as the
local (x, y) and derive the standard microstructure quantities used on a trading
desk: execution price, price impact / slippage, market depth, and LP impermanent
loss. Working in ETH terms keeps every result exact and independent of the ETH/EUR
rate; EUR figures use a single documented spot assumption.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class Pool:
    # Virtual reserves reconstructed from the REAL on-chain liquidity L and
    # sqrtPriceX96 (Base block #49023454, 2026-07-23). See data/pool_state.json.
    x: float = 0.003          # ETH reserve (currency0)
    y: float = 65_992_981.0   # HLD reserve (currency1)
    fee: float = 0.01         # LP fee (1%, verified on-chain: lpFee = 10000 pips)

    @property
    def k(self) -> float:
        return self.x * self.y

    @property
    def spot_hld_per_eth(self) -> float:
        return self.y / self.x

    @property
    def spot_eth_per_hld(self) -> float:
        return self.x / self.y

    # ------- trade execution (buy HLD by sending ETH) -------
    def buy_hld(self, dx_eth: float) -> dict:
        """Send dx_eth ETH, receive HLD. Returns execution metrics."""
        dx = dx_eth * (1 - self.fee)          # fee taken on input
        x_new = self.x + dx
        y_new = self.k / x_new
        hld_out = self.y - y_new
        eff_eth_per_hld = dx_eth / hld_out    # effective price incl. fee
        slippage = eff_eth_per_hld / self.spot_eth_per_hld - 1
        return {
            "eth_in": dx_eth,
            "hld_out": hld_out,
            "effective_eth_per_hld": eff_eth_per_hld,
            "slippage": slippage,
            "new_price_hld_per_eth": y_new / x_new,
        }

    # ------- market depth -------
    def eth_to_move_price(self, pct_up: float) -> float:
        """Gross ETH input (incl. fee) required to push HLD price up by pct_up."""
        r = 1 + pct_up
        x_new = np.sqrt(self.k * (self.x / self.y) * r)
        return (x_new - self.x) / (1 - self.fee)


def impermanent_loss(price_ratio):
    """IL vs HODL for a 50/50 CPMM position. price_ratio = P_final / P_initial."""
    r = np.asarray(price_ratio, dtype=float)
    return 2 * np.sqrt(r) / (1 + r) - 1


if __name__ == "__main__":
    p = Pool()
    print("spot: 1 ETH =", f"{p.spot_hld_per_eth:,.0f}", "HLD")
    for eur in (1, 5, 10):
        m = p.buy_hld(eur / 1645.88)   # real ETH/EUR, 2026-07-23
        print(f"buy {eur:>2}EUR -> slippage {m['slippage']*100:6.1f}%  "
              f"HLD_out {m['hld_out']:,.0f}")
    print("IL at r=2:", f"{impermanent_loss(2)*100:.2f}%")
