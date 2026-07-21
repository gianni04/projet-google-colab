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
| **Parametric (Variance-Covariance)** | Fits a normal distribution to portfolio returns using the covariance matrix | Returns are normally distributed |
| **Monte Carlo Simulation** | Generates 50,000 correlated daily return paths via Cholesky decomposition | Normality + covariance structure |

### Portfolios tested

- **Single asset — UBS Group (UBS):**  
  Historical VaR 99%: **-5.64%** | CVaR 99%: **-8.51%**

- **Single asset — Bitcoin (BTC-USD):**  
  Historical VaR 99%: **-8.91%** | CVaR 99%: **-13.24%**

- **Diversified portfolio (9 assets):**  
  LVMH, Sanofi, L'Oréal, Airbus (FR equities, 40%) + Apple, Microsoft, NVIDIA (US tech, 30%) + TLT bond ETF (20%) + Ethereum (10%)  
  Historical VaR 99%: **-3.24%** | CVaR 99%: **-4.58%**

### Key result
The three methodologies diverge most on fat-tailed assets (BTC): Historical Simulation captures extreme tail events better than the Parametric approach, which underestimates tail risk by assuming normality. Monte Carlo and Parametric converge on near-Gaussian assets (UBS, diversified portfolio), confirming the model's coherence.

### Visualisation
Interactive Plotly charts overlay the three return distributions with their respective VaR lines for each portfolio.

### Stack
```
Python · NumPy · pandas · SciPy · yfinance · Plotly
```

---

## 2. Options Pricing & Greeks — Black-Scholes Model

**Notebook:** `option.ipynb`  
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gianni04/projet-google-colab/blob/main/option.ipynb)

### What it does
Implements the **Black-Scholes analytical model** to price European call and put options and computes the full set of **Greeks** to quantify the sensitivity of option value to changes in market inputs.

### Greeks computed

| Greek | Measures sensitivity to |
|---|---|
| **Delta (Δ)** | Change in underlying price |
| **Gamma (Γ)** | Rate of change of Delta |
| **Vega (ν)** | Implied volatility |
| **Theta (Θ)** | Time decay (passage of time) |
| **Rho (ρ)** | Risk-free interest rate |

### Why it matters
Greeks are the primary tool used by risk desks and options traders to hedge and monitor derivative exposure. Delta and Gamma drive dynamic hedging strategies; Vega and Theta determine the cost of holding options positions over time.

### Stack
```
Python · NumPy · pandas · SciPy · Matplotlib
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

All notebooks run directly in Google Colab — no local installation required. Click any **Open in Colab** badge above to launch.

To run locally:
```bash
pip install numpy pandas scipy yfinance matplotlib plotly
```

---

## Author

**Gianni Pilotti**  
Economics & Finance Student — Portfolio Risk & Quantitative Methods  
University of Luxembourg (Bachelor, expected January 2027)  
[LinkedIn](https://www.linkedin.com/in/gianni-pilotti-9152832a4/) · [GitHub](https://github.com/gianni04)
