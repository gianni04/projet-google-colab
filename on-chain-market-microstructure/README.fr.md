# Micro-structure du marché HLD

Analyse de la micro-structure du pool Uniswap V4 **HLD/ETH** sur la blockchain
**Base** (chain ID 8453).

## Pool

| Champ | Valeur |
|-------|--------|
| PoolManager | `0x498581fF718922c3f8e6A244956aF099B2652b2b` |
| Token HLD | `0xd5b6cd58d75544aAD829CaE5396eb1fD53969dBa` |
| currency0 | ETH natif (`0x0000...0000`) |
| currency1 | HLD |
| Frais | 1 % (10000 pips) |
| Tick spacing | 200 |
| Hooks | Aucun |

## Données

Les données de prix et de liquidité sont **réelles**, extraites on-chain via
`extract_live.py` qui lit les slots de stockage du PoolManager via `extsload(bytes32)`.

Les courbes de coût d'exécution (slippage) sont des sorties de **modèle**
constant-product (x * y = k) appliquées aux réserves réelles. Ce ne sont PAS
des transactions observées. Toujours lire « coût d'exécution modélisé ».

- **Dernière extraction**: Bloc #49023454 (2026-07-23)
- **Prix ETH/EUR**: 1 645,88 € (CoinGecko, 2026-07-23)
- **Prix spot**: 1 ETH = 21,997,497,896 HLD (1 HLD ≈ 0.00000000004546 ETH ≈ 0.000075 €)
- **Liquidité L**: 444,949,887,904,857,917,931

## Structure

```
HLD-market-microstructure/
├── extract_live.py        # Extraction on-chain
├── src/
│   └── plots.py           # Visualisations (coût d'exécution modélisé, depth)
├── notebooks/
│   └── analysis.ipynb     # Notebook d'analyse
├── data/
│   └── pool_state.json    # État du pool extrait
├── figures/               # Graphiques générés
├── README.md
└── README.fr.md
```

## Utilisation

```bash
# 1. Extraire les données live
python extract_live.py

# 2. Régénérer les figures
python src/plots.py

# 3. Lancer le notebook
jupyter notebook notebooks/analysis.ipynb
```

## Vérification

Pour recouper les données sur BaseScan:
1. Aller sur https://basescan.org/address/0x498581fF718922c3f8e6A244956aF099B2652b2b#readContract
2. Fonction `extsload(bytes32)` avec le `stateSlot` (affiché par `extract_live.py`)
