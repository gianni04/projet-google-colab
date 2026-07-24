"""
onchain.py — Uniswap V4 pool-state extraction for the HLD/ETH pool on Base.

Uniswap V4 stores every pool inside a single Singleton contract (the PoolManager).
There is no per-pool contract to call, and Slot0 is NOT exposed by a public getter:
it must be read with the raw storage-access function `extsload(bytes32 slot)`.

This module shows the full, reproducible derivation:

  1. Build the PoolKey (currency0, currency1, fee, tickSpacing, hooks).
  2. poolId       = keccak256(abi.encode(PoolKey)).
  3. stateSlot    = keccak256(abi.encode(poolId, uint256(POOLS_MAPPING_SLOT))).
     (`mapping(PoolId => Pool.State) _pools` lives at storage slot 6.)
  4. word         = extsload(stateSlot)          # Slot0, packed
  5. decode Slot0 = (sqrtPriceX96 | tick | protocolFee | lpFee).
  6. price        = (sqrtPriceX96 / 2**96) ** 2  # currency1 per currency0.

Run offline (uses the values recorded in data/pool_state.json):
    python src/onchain.py
Run live against a Base RPC:
    python src/onchain.py --live --rpc https://mainnet.base.org
"""
from __future__ import annotations
import argparse
from eth_abi import encode
from eth_hash.auto import keccak

# --- Immutable pool parameters (the "fiche technique") -----------------------
POOL_MANAGER = "0x498581fF718922c3f8e6A244956aF099B2652b2b"
HLD          = "0xd5b6cd58d75544aAD829CaE5396eb1fD53969dBa"
NATIVE_ETH   = "0x0000000000000000000000000000000000000000"
FEE          = 10000   # 1% expressed in pips (1e6 = 100%)
TICK_SPACING = 200
HOOKS        = "0x0000000000000000000000000000000000000000"
POOLS_MAPPING_SLOT = 6  # storage slot of `_pools` in PoolManager


def pool_id(currency0=NATIVE_ETH, currency1=HLD, fee=FEE,
            tick_spacing=TICK_SPACING, hooks=HOOKS) -> bytes:
    """PoolId = keccak256(abi.encode(PoolKey)). currency0 must be the lower address."""
    if int(currency0, 16) > int(currency1, 16):
        currency0, currency1 = currency1, currency0
    packed = encode(
        ["address", "address", "uint24", "int24", "address"],
        [currency0, currency1, fee, tick_spacing, hooks],
    )
    return keccak(packed)


def state_slot(pid: bytes, mapping_slot: int = POOLS_MAPPING_SLOT) -> bytes:
    """Storage slot of Pool.State for a given poolId (Solidity mapping layout)."""
    return keccak(encode(["bytes32", "uint256"], [pid, mapping_slot]))


def decode_slot0(word: int) -> dict:
    """Unpack the packed Slot0 word read from storage.
    Layout (low -> high bits): sqrtPriceX96 (160) | tick (24) | protocolFee (24) | lpFee (24).
    """
    sqrt_price_x96 = word & ((1 << 160) - 1)
    tick_u = (word >> 160) & ((1 << 24) - 1)
    tick = tick_u - (1 << 24) if tick_u >= (1 << 23) else tick_u  # int24 two's complement
    protocol_fee = (word >> 184) & ((1 << 24) - 1)
    lp_fee = (word >> 208) & ((1 << 24) - 1)
    return {
        "sqrtPriceX96": sqrt_price_x96,
        "tick": tick,
        "protocolFee": protocol_fee,
        "lpFee": lp_fee,
        "price_c1_per_c0": (sqrt_price_x96 / 2 ** 96) ** 2,
    }


def extsload_live(rpc_url: str, slot: bytes) -> int:
    """Call PoolManager.extsload(bytes32) via a Base RPC and return the word as int."""
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    abi = [{"inputs": [{"internalType": "bytes32", "name": "slot", "type": "bytes32"}],
            "name": "extsload",
            "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
            "stateMutability": "view", "type": "function"}]
    pm = w3.eth.contract(address=Web3.to_checksum_address(POOL_MANAGER), abi=abi)
    return int.from_bytes(pm.functions.extsload(slot).call(), "big")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="read live from a Base RPC")
    ap.add_argument("--rpc", default="https://mainnet.base.org")
    args = ap.parse_args()

    pid = pool_id()
    slot = state_slot(pid)
    print("PoolId    :", "0x" + pid.hex())
    print("StateSlot :", "0x" + slot.hex())

    if args.live:
        word = extsload_live(args.rpc, slot)
        print("Slot0 word:", hex(word))
        print("Decoded   :", decode_slot0(word))
    else:
        # offline demonstration using recorded reserves
        import math
        x, y = 0.003, 65_993_467
        price = y / x
        sqrt_price_x96 = int(math.sqrt(price) * 2 ** 96)
        print("(offline) implied sqrtPriceX96:", sqrt_price_x96)
        print("(offline) 1 ETH =", f"{price:,.0f}", "HLD")


if __name__ == "__main__":
    main()
