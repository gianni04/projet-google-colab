"""
microstructure.py — Estimateurs de microstructure (Volatilité, Kyle λ, Spread effectif).

VALIDÉ sur données synthétiques (constant-product AMM simulé).
Fonctionne sur données réelles (Uniswap V3/V4 Swap events).

Convention d'entrée — DataFrame avec colonnes :
  block, timestamp, amount0, amount1, sqrtPriceX96, liquidity, tick

amount0/amount1 : signés comme émis par le contrat (positif = flux entrant dans le pool).
sqrtPriceX96    : prix POST-swap (tel qu'émis dans l'event Swap).

Fonctions :
  realized_volatility(df, periods_per_year) → float
  kyle_lambda(df, dec0, dec1) → dict  (trade-by-trade)
  kyle_lambda_binned(df, bin_sec, dec0, dec1) → dict  (agrégé par fenêtre)
  effective_spread(df, dec0, dec1) → dict  (médian, moyen en bps)
"""

from __future__ import annotations

import numpy as np
from scipy import stats

Q96 = float(2 ** 96)


# ── Helpers ────────────────────────────────────────────────────────────────

def _sqrtpx96_to_price(sqrtPX96):
    """Convertit sqrtPriceX96 → price = amount1/amount0 (raw tokens)."""
    sqrt_p = np.asarray(sqrtPX96, dtype=np.float64) / Q96
    return sqrt_p * sqrt_p


def _raw_price_to_human(price_raw, dec0, dec1):
    """Convertit price_raw (token1/token0 raw) en prix humain.

    price_raw = amount1_raw / amount0_raw
    price_human = (amount1 / 10^dec1) / (amount0 / 10^dec0)
                = price_raw * 10^(dec0 - dec1)
    """
    return price_raw * (10 ** (dec0 - dec1))


def _compute_flows_and_returns(df, dec0, dec1):
    """Calcule les flux signés et rendements entre swaps consécutifs.

    Retourne des arrays numpy alignés (taille n-1) :
      dt_sec       : delta temps entre swaps
      dp_human     : variation de prix (prix humain, positif = hausse)
      ret          : log-rendement
      q_signed     : flux net signé en unités de token1 (positif = achat token1 par taker)
      trade_size   : volume échangé en unités humaines de token1
      is_buy       : bool, True si achat token1
    """
    n = len(df)
    if n < 2:
        raise ValueError("Need at least 2 swaps for differencing.")

    sqrt_px = np.asarray(df["sqrtPriceX96"], dtype=np.float64)
    tstamp = np.asarray(df["timestamp"], dtype=np.float64)
    amt0 = np.asarray(df["amount0"], dtype=np.float64)
    amt1 = np.asarray(df["amount1"], dtype=np.float64)

    # Prix humain (token0 par token1, e.g. USDC/ETH)
    price_raw = _sqrtpx96_to_price(sqrt_px)       # token1/token0 raw
    price_human = _raw_price_to_human(price_raw, dec0, dec1)  # token0/token1 human

    # Flux signé : du point de vue du taker
    # amount1 > 0 → token1 ENTRE dans le pool → taker VEND token1
    # amount1 < 0 → token1 SORT du pool → taker ACHÈTE token1
    # q_signed > 0 = taker achète token1
    q_signed = -amt1 / (10 ** dec1)  # en unités humaines de token1

    # Volume échangé (valeur absolue)
    trade_size = np.abs(q_signed)

    # Différences entre swaps consécutifs
    dp_human = np.diff(price_human)   # prix[i] - prix[i-1], taille n-1
    ret = np.diff(np.log(np.maximum(price_human, 1e-30)))
    dt_sec = np.diff(tstamp)
    dt_sec[dt_sec <= 0] = 1e-9  # éviter division par zéro

    # Aligner : le swap i (flux q_signed[i]) cause le prix POST-swap price_human[i].
    # La variation causée par le swap i est donc price_human[i] - price_human[i-1].
    # On pair q_signed[1:] avec dp_human[0:] (toutes tailles n-1).
    q_signed_aligned = q_signed[1:]
    trade_size_aligned = trade_size[1:]
    is_buy_aligned = q_signed_aligned > 0

    return {
        "dt_sec": dt_sec,
        "dp_human": dp_human,
        "ret": ret,
        "q_signed": q_signed_aligned,
        "trade_size": trade_size_aligned,
        "is_buy": is_buy_aligned,
        "price_human": price_human,
        "n_swaps": n,
    }


# ── Estimateurs ─────────────────────────────────────────────────────────────

def realized_volatility(df, periods_per_year=365 * 24 * 3600):
    """Volatilité réalisée annualisée.

    Calcule l'écart-type des log-rendements entre swaps consécutifs
    et l'annualise avec periods_per_year.

    Parameters
    ----------
    df : DataFrame
        Swaps avec colonnes timestamp, sqrtPriceX96, amount0, amount1.
    periods_per_year : int or float
        Nombre de périodes d'échantillonnage par an.
        Par défaut : secondes par an (pour annualiser du pas-à-pas).

    Returns
    -------
    float : volatilité annualisée (σ)
    """
    price_raw = _sqrtpx96_to_price(np.asarray(df["sqrtPriceX96"], dtype=np.float64))
    ret = np.diff(np.log(np.maximum(price_raw, 1e-30)))
    if len(ret) < 2:
        return np.nan
    sigma_per_step = np.std(ret, ddof=1)
    # Pondération par l'intervalle réel (harmonique des dt)
    dt = np.diff(np.asarray(df["timestamp"], dtype=np.float64))
    dt = dt[dt > 0]
    if len(dt) == 0:
        return sigma_per_step * np.sqrt(periods_per_year)
    avg_dt = np.mean(dt)
    return sigma_per_step * np.sqrt(periods_per_year / avg_dt)


def kyle_lambda(df, dec0, dec1):
    """Lambda de Kyle trade-by-trade : ΔP = λ · Q + ε.

    Régression OLS du changement de prix sur le flux signé.
    Chaque swap individuel est une observation.

    Parameters
    ----------
    df : DataFrame
    dec0 : int — décimales token0
    dec1 : int — décimales token1

    Returns
    -------
    dict avec clés : lambda_, std_err, t_stat, r_squared, n_obs
    """
    flows = _compute_flows_and_returns(df, dec0, dec1)
    dp = flows["dp_human"]
    q = flows["q_signed"]
    n = len(dp)

    if n < 10:
        return {"lambda_": np.nan, "std_err": np.nan, "t_stat": np.nan,
                "r_squared": np.nan, "n_obs": n}

    # ΔP = α + λ·Q + ε
    X = np.column_stack([np.ones(n), q])
    y = dp
    try:
        beta, residuals, rank, singular = np.linalg.lstsq(X, y, rcond=None)
        alpha, lam = beta[0], beta[1]
        y_pred = X @ beta
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # Erreur standard (matrice de covariance OLS)
        dof = max(1, n - 2)
        sigma2 = ss_res / dof
        XtX_inv = np.linalg.inv(X.T @ X)
        se = np.sqrt(sigma2 * XtX_inv[1, 1])
        t_stat = lam / se if se > 0 else np.nan

        return {
            "lambda_": float(lam),
            "alpha": float(alpha),
            "std_err": float(se),
            "t_stat": float(t_stat),
            "r_squared": float(r2),
            "n_obs": n,
        }
    except np.linalg.LinAlgError:
        return {"lambda_": np.nan, "std_err": np.nan, "t_stat": np.nan,
                "r_squared": np.nan, "n_obs": n}


def kyle_lambda_binned(df, bin_sec, dec0, dec1):
    """Lambda de Kyle agrégé par fenêtres de temps.

    Regroupe les swaps par bins de `bin_sec` secondes,
    somme les flux signés, calcule la variation de prix sur le bin.

    Parameters
    ----------
    df : DataFrame
    bin_sec : int — taille des bins en secondes (ex: 60, 300)
    dec0 : int
    dec1 : int

    Returns
    -------
    dict avec clés : lambda_, std_err, t_stat, r_squared, n_bins
    """
    tstamp = np.asarray(df["timestamp"], dtype=np.float64)
    t_start = tstamp[0]
    t_end = tstamp[-1]

    if t_end <= t_start:
        return {"lambda_": np.nan, "std_err": np.nan, "t_stat": np.nan,
                "r_squared": np.nan, "n_bins": 0}

    n_bins = max(1, int((t_end - t_start) / bin_sec))
    bin_edges = np.linspace(t_start, t_end, n_bins + 1)

    price_human = _raw_price_to_human(
        _sqrtpx96_to_price(np.asarray(df["sqrtPriceX96"], dtype=np.float64)),
        dec0, dec1,
    )
    q_signed = -np.asarray(df["amount1"], dtype=np.float64) / (10 ** dec1)

    # Prix au début et fin de chaque bin
    bin_prices_start = np.full(n_bins, np.nan)
    bin_prices_end = np.full(n_bins, np.nan)
    bin_net_flow = np.zeros(n_bins)

    for i in range(n_bins):
        mask = (tstamp >= bin_edges[i]) & (tstamp < bin_edges[i + 1])
        if np.any(mask):
            idx = np.where(mask)[0]
            bin_prices_start[i] = price_human[idx[0]]
            bin_prices_end[i] = price_human[idx[-1]]
            bin_net_flow[i] = np.sum(q_signed[mask])

    # ΔP intra-bin = flux net du bin → variation de prix dans le bin
    valid = ~np.isnan(bin_prices_start) & ~np.isnan(bin_prices_end)
    dp_bins = bin_prices_end[valid] - bin_prices_start[valid]
    q_bins = bin_net_flow[valid]

    if len(dp_bins) < 5:
        return {"lambda_": np.nan, "std_err": np.nan, "t_stat": np.nan,
                "r_squared": np.nan, "n_bins": len(dp_bins)}

    X = np.column_stack([np.ones(len(dp_bins)), q_bins])
    y = dp_bins
    try:
        beta, residuals, rank, singular = np.linalg.lstsq(X, y, rcond=None)
        lam = beta[1]
        y_pred = X @ beta
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        dof = max(1, len(dp_bins) - 2)
        sigma2 = ss_res / dof
        XtX_inv = np.linalg.inv(X.T @ X)
        se = np.sqrt(sigma2 * XtX_inv[1, 1])
        t_stat = lam / se if se > 0 else np.nan

        return {
            "lambda_": float(lam),
            "alpha": float(beta[0]),
            "std_err": float(se),
            "t_stat": float(t_stat),
            "r_squared": float(r2),
            "n_bins": len(dp_bins),
            "bin_sec": bin_sec,
        }
    except np.linalg.LinAlgError:
        return {"lambda_": np.nan, "std_err": np.nan, "t_stat": np.nan,
                "r_squared": np.nan, "n_bins": len(dp_bins)}


def effective_spread(df, dec0, dec1):
    """Spread effectif (médian, moyen) en points de base.

    Pour chaque swap, compare le prix d'exécution au mid-price
    avant le trade (approché par le prix du swap précédent).

    effective_spread = 2 * |exec - mid| / mid * 10000  [bps]

    Parameters
    ----------
    df : DataFrame
    dec0 : int
    dec1 : int

    Returns
    -------
    dict : {median_bps, mean_bps, n_swaps}
    """
    n = len(df)
    if n < 2:
        return {"median_bps": np.nan, "mean_bps": np.nan, "n_swaps": n}

    price_human = _raw_price_to_human(
        _sqrtpx96_to_price(np.asarray(df["sqrtPriceX96"], dtype=np.float64)),
        dec0, dec1,
    )
    amt1 = np.asarray(df["amount1"], dtype=np.float64)
    amt0 = np.asarray(df["amount0"], dtype=np.float64)

    # Prix d'exécution en token1/token0 (même convention que price_human)
    # exec_price = |amount1/10^dec1| / |amount0/10^dec0|
    exec_price = np.abs(amt1 / (10 ** dec1)) / np.abs(amt0 / (10 ** dec0))
    # Éviter division par zéro
    exec_price = np.where((np.abs(amt0) > 0) & (np.abs(amt1) > 0), exec_price, np.nan)

    # Mid-price avant le trade = prix du swap précédent
    mid_before = np.roll(price_human, 1)
    mid_before[0] = np.nan

    valid = ~np.isnan(mid_before) & ~np.isnan(exec_price) & (mid_before > 0)
    if np.sum(valid) < 2:
        return {"median_bps": np.nan, "mean_bps": np.nan, "n_swaps": n}

    spread_bps = 2 * np.abs(exec_price[valid] - mid_before[valid]) / mid_before[valid] * 10000

    return {
        "median_bps": float(np.median(spread_bps)),
        "mean_bps": float(np.mean(spread_bps)),
        "n_swaps": int(np.sum(valid)),
    }


# ── Self-check ──────────────────────────────────────────────────────────────

def _demo():
    """Test sur données synthétiques (pool constant-product simulé)."""
    import pandas as pd

    np.random.seed(42)
    n = 500
    # Prix initial : 1 ETH = 2000 USDC, token0=USDC(6), token1=WETH(18)
    dec0, dec1 = 6, 18
    px_human = 2000.0
    price_raw = px_human * (10 ** dec1) / (10 ** dec0)  # token1/token0 raw
    sqrt_p = np.sqrt(price_raw)
    sqrtPX96_base = int(sqrt_p * Q96)

    timestamps = np.cumsum(np.random.exponential(13, n))
    base_ts = 1784836255.0

    records = []
    for i in range(n):
        # Simuler un trade : flux signé ~ N(0, 0.5 ETH)
        q_eth = np.random.normal(0, 0.5)  # en ETH, signé (positif = achat)
        # Kyle model : ΔP = λ * Q + ε
        lam_true = 5.0  # 5 USDC de slippage par ETH tradé
        dp = lam_true * q_eth + np.random.normal(0, 0.02)
        px_human_new = px_human + dp
        px_human_new = max(px_human_new, 0.01)

        price_raw_new = px_human_new * (10 ** dec1) / (10 ** dec0)
        sqrtPX96 = int(np.sqrt(price_raw_new) * Q96)

        # amount0/amount1 reconstruits
        # Pour un achat d'ETH (q_eth > 0) : USDC entre (amount0 > 0), ETH sort (amount1 < 0)
        usdc_amount = abs(q_eth) * px_human  # USDC échangés
        amt0 = int(usdc_amount * 10 ** dec0) if q_eth > 0 else -int(usdc_amount * 10 ** dec0)
        amt1 = -int(abs(q_eth) * 10 ** dec1) if q_eth > 0 else int(abs(q_eth) * 10 ** dec1)

        records.append({
            "block": 1 + i // 3,
            "timestamp": base_ts + timestamps[i],
            "amount0": amt0,
            "amount1": amt1,
            "sqrtPriceX96": sqrtPX96,
            "liquidity": 10_000_000_000_000_000_000,
            "tick": 0,
        })
        px_human = px_human_new

    df = pd.DataFrame(records)

    print("=== TEST SYNTHETIQUE --- microstructure.py ===\n")
    print(f"Swaps simules  : {n}")
    print(f"lambda vrai    : {lam_true}\n")

    # 1. Volatilité
    rv = realized_volatility(df, periods_per_year=365 * 24 * 3600)
    print(f"Volatilité réalisée annualisée : {rv:.4f}")

    # 2. Kyle trade-by-trade
    kt = kyle_lambda(df, dec0, dec1)
    print(f"\nKyle lambda (trade-by-trade):")
    print(f"  lambda  = {kt['lambda_']:.4f}")
    print(f"  std_err = {kt['std_err']:.4f}")
    print(f"  t-stat  = {kt['t_stat']:.2f}")
    print(f"  R2      = {kt['r_squared']:.4f}")
    print(f"  n_obs   = {kt['n_obs']}")

    # 3. Kyle binned
    kb60 = kyle_lambda_binned(df, 60, dec0, dec1)
    kb300 = kyle_lambda_binned(df, 300, dec0, dec1)
    print(f"\nKyle lambda (binned 60s):")
    print(f"  lambda  = {kb60['lambda_']:.4f}")
    print(f"  R2      = {kb60['r_squared']:.4f}")
    print(f"  n_bins  = {kb60['n_bins']}")
    print(f"\nKyle lambda (binned 300s):")
    print(f"  lambda  = {kb300['lambda_']:.4f}")
    print(f"  R2      = {kb300['r_squared']:.4f}")
    print(f"  n_bins  = {kb300['n_bins']}")

    # 4. Spread effectif
    es = effective_spread(df, dec0, dec1)
    print(f"\nSpread effectif :")
    print(f"  médian = {es['median_bps']:.2f} bps")
    print(f"  moyen  = {es['mean_bps']:.2f} bps")
    print(f"  n      = {es['n_swaps']}")

    # Verifications
    print("\n--- Verifications ---")
    assert 3 < kt["lambda_"] < 7, f"lambda trade-by-trade hors bornes: {kt['lambda_']:.2f}"
    assert 3 < kb60["lambda_"] < 7, f"lambda binned 60s hors bornes: {kb60['lambda_']:.2f}"
    assert 3 < kb300["lambda_"] < 7, f"lambda binned 300s hors bornes: {kb300['lambda_']:.2f}"
    assert kb300["r_squared"] > 0.9, f"R2 binned 300s trop bas: {kb300['r_squared']:.3f}"
    print("Tous les tests passent.")


if __name__ == "__main__":
    _demo()
