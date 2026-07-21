# Quantitative Finance Projects — Python

A collection of quantitative finance models built in Python (Google Colab), covering portfolio risk measurement, derivatives pricing, and yield curve analysis.

---

## 1. Portfolio Risk — VaR & CVaR (Three Methodologies)

**Notebook:** `Var+Cvar+Monte_carlo.ipynb`  
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gianni04/projet-google-colab/blob/main/Var%2BCvar%2BMonte_carlo.ipynb)

### What it does
Implements and compares three industry-standard methodologies to estimate **Value at Risk (VaR)** and **Conditional VaR (CVaR / Expected Shortfall)** at the 99% confidence level on real market data fetched via `yfinance`.

### Methodologies compared

| Method | Approach | Key assumption |
|---|---|---|
| **Historical Simulation** | Sorts actual log-returns and reads the 1st percentile | No distributional assumption |
| **Parametric (Variance-Covariance)** | Fits a normal distribution using the covariance matrix | Returns are normally distributed |
| **Monte Carlo Simulation** | Generates 50,000 correlated daily paths via Cholesky decomposition | Normality + covariance structure |

### Portfolios tested

- **Single asset — UBS Group:**  
  Historical VaR 99%: **-5.64%** | CVaR 99%: **-8.51%**

- **Single asset — Bitcoin (BTC-USD):**  
  Historical VaR 99%: **-8.91%** | CVaR 99%: **-13.24%**

- **Diversified portfolio (9 assets):**  
  LVMH, Sanofi, L'Oréal, Airbus (FR, 40%) + Apple, Microsoft, NVIDIA (US, 30%) + TLT bonds (20%) + Ethereum (10%)  
  Historical VaR 99%: **-3.24%** | CVaR 99%: **-4.58%**

### Key result
The three methodologies diverge most on fat-tailed assets (BTC): Historical Simulation captures extreme tail events better than Parametric, which underestimates tail risk by assuming normality. Monte Carlo and Parametric converge on near-Gaussian assets (UBS, diversified portfolio), confirming the model's coherence.

### Stack
```
Python · NumPy · pandas · SciPy · yfinance · Plotly
```

---

## 2. Options Pricing Engine — Black-Scholes & Binomial Tree

**Notebook:** `option.ipynb`  
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gianni04/projet-google-colab/blob/main/option.ipynb)

### What it does
A full options pricing engine built around two models and an object-oriented architecture (`VanillaOption`, `MarketEnvironment`, `BlackScholesPricer`, `BinomialTreePricer`).

### Model 1 — Black-Scholes (European options)

Analytical closed-form pricing with dividends (`q`) for European calls and puts, including four Greeks:

| Greek | Formula basis | Normalisation |
|---|---|---|
| **Delta (Δ)** | `e^{-qT} · N(d1)` | Raw (0 to ±1) |
| **Gamma (Γ)** | `e^{-qT} · N'(d1) / (S·σ·√T)` | Raw |
| **Vega (ν)** | `S · e^{-qT} · N'(d1) · √T` | Divided by 100 (per 1% vol move) |
| **Theta (Θ)** | Full expression with both carry terms | Divided by 365 (daily decay) |

### Model 2 — Binomial Tree CRR (American options)

Cox-Ross-Rubinstein binomial tree with backward induction and early exercise check at each node. Convergence to Black-Scholes confirmed on European options.

**Example output** (S=100, K=100, T=1y, r=5%, q=2%, σ=20%):
```
BSM Call European    : 10.XXXX
Binomial Call European : 10.XXXX  → converges to BSM
Binomial Call American : 10.XXXX  → early exercise premium
```

### Visualisations

- **Interactive Greeks dashboard** (ipywidgets sliders): real-time Price / Delta / Gamma / Theta curves for any Call or Put, with ATM strike line
- **American vs European price comparison**: side-by-side curves + early exercise premium filled area
- **3D Implied Volatility Surface**: Strike × Maturity grid with moneyness skew (`-0.12 × (K/S - 1)`) and term structure (`0.04 / √T`)
- **3D American Premium Surface**: Spot × Maturity grid of `Price_American - Price_BSM` (Inferno colorscale)

### Stack
```
Python · NumPy · SciPy · Plotly · ipywidgets
```

---

## 3. EUR/US Yield Curve Analysis

**Notebook:** `EUR_US_Yield_Curveipynb.ipynb`  
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gianni04/projet-google-colab/blob/main/EUR_US_Yield_Curveipynb.ipynb)

### What it does
Analyses and visualises the EUR and USD government yield curves across maturities, exploring the term structure of interest rates and key spread dynamics.

### Stack
```
Python · pandas · Matplotlib
```

---

## Setup

All notebooks run directly in Google Colab — no local installation required. Click any **Open in Colab** badge above.

To run locally:
```bash
pip install numpy pandas scipy yfinance matplotlib plotly ipywidgets
```

---

## Author

**Gianni Pilotti**  
Economics & Finance Student — Portfolio Risk & Quantitative Methods  
University of Luxembourg (Bachelor, expected January 2027)  
[LinkedIn](https://www.linkedin.com/in/gianni-pilotti-9152832a4/) · [GitHub](https://github.com/gianni04)
