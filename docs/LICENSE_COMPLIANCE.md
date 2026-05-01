# License Compliance & Attribution Policy

## 1. Overview
This policy defines the standards and procedures for open-source license compliance within the MT5 Trading Bot project. Our goal is to ensure that all third-party software integrated into the codebase is used in accordance with its licensing terms, ensuring legal safety and respecting intellectual property.

## 2. Permitted Licenses
The following licenses are generally permitted for use in this project:

- **MIT License**
- **Apache License 2.0**
- **BSD (2-Clause and 3-Clause)**
- **Python Software Foundation (PSF) License**
- **ISC License**
- **Mozilla Public License 2.0 (MPL 2.0)** - *Permitted as external dependencies*
- **GNU Lesser General Public License (LGPL)** - *Permitted as external dependencies; strictly monitored*

## 3. Disallowed Licenses
The following licenses are strictly prohibited from being integrated into the core codebase or included as dependencies without explicit legal review and architectural isolation:

- **GNU General Public License (GPL) v1, v2, v3**
- **GNU Affero General Public License (AGPL)**
- **Server Side Public License (SSPL)**
- **Creative Commons Non-Commercial (CC-BY-NC)**
- **Proprietary licenses with restrictive redistribution terms**

## 4. Integration Requirements
For any code integrated directly from other open-source repositories (not via package managers), the following steps are mandatory:

1. **License Inclusion**: Copy the original `LICENSE` file from the source repository to the integration point (e.g., `src/external/{repo_name}/LICENSE`).
2. **Attribution**: Add a header comment to each integrated file:
   ```python
   # Based on {RepoName} ({URL})
   # Licensed under {LicenseType}
   # Copyright (c) {Year} {OriginalAuthors}
   ```
3. **Audit Log**: Record the integration in the `ATTRIBUTIONS.md` file in the repository root.

## 5. Automated Compliance Checks
This repository employs automated license scanning via GitHub Actions (`.github/workflows/license-check.yml`). The CI pipeline will fail if:
- A dependency with a disallowed license is detected.
- An unknown license is found (requires manual verification).

## 6. Integrated Components Detailed

### MIT Licensed Repositories

#### 1. zero-was-here/tradingbot
- **License:** MIT
- **URL:** https://github.com/zero-was-here/tradingbot
- **Copyright:** zero-was-here (2024)
- **Included Components:** PPO algorithm, Dreamer V3, feature engineering.
- **Attribution:** `src/core/rl_algorithms/ppo/`
- **Status:** ✅ Compliant

#### 2. ilahuerta-IA/mt5_live_trading_bot
- **License:** MIT
- **URL:** https://github.com/ilahuerta-IA/mt5_live_trading_bot
- **Copyright:** ilahuerta-IA (2024)
- **Included Components:** Portfolio allocation, 6-layer entry filter, state machine, GUI monitor.
- **Attribution:** `src/core/risk_management/` and `src/core/features/`
- **Status:** ✅ Compliant

#### 3. CodeDestroyer19/Neural-Network-MT5-Trading-Bot
- **License:** MIT
- **URL:** https://github.com/CodeDestroyer19/Neural-Network-MT5-Trading-Bot
- **Copyright:** CodeDestroyer19 (2023)
- **Included Components:** Neural network architecture, technical indicator calculations.
- **Attribution:** `src/core/rl_algorithms/neural_networks/`
- **Status:** ✅ Compliant

#### 4. AminHP/gym-mtsim
- **License:** MIT
- **URL:** https://github.com/AminHP/gym-mtsim
- **Copyright:** AminHP (2022)
- **Included Components:** OpenAI Gym environment wrapper, MetaTrader 5 simulator.
- **Attribution:** `src/core/environments/gym_mt5/`
- **Status:** ✅ Compliant

#### 5. Stefodan21/Forex-trading-bot
- **License:** MIT
- **URL:** https://github.com/Stefodan21/Forex-trading-bot
- **Copyright:** Stefodan21 (2023)
- **Included Components:** PPO variant, GPU acceleration (DirectML/OpenCL), position sizing.
- **Attribution:** `src/core/rl_algorithms/ppo_gpu/`
- **Status:** ✅ Compliant

#### 6. geraked/metatrader5
- **License:** MIT
- **URL:** https://github.com/geraked/metatrader5
- **Copyright:** geraked (2023)
- **Included Components:** MQL5 trading strategies, Expert Advisor templates.
- **Attribution:** `src/strategies/templates/`
- **Status:** ✅ Compliant

### Apache 2.0 Licensed Repositories

#### 1. nguyenviettuan96/mt5_AI_trading_bot
- **License:** Apache 2.0
- **URL:** https://github.com/nguyenviettuan96/mt5_AI_trading_bot
- **Copyright:** nguyenviettuan96 (2023)
- **Included Components:** LSTM neural network, RL integration, feature extraction.
- **Attribution:** `src/core/rl_algorithms/lstm/`
- **Status:** ✅ Compliant

### Special Verification Required

#### nkanven/MT4-MT5-Trading-EA-Collections
- **License Type:** MQL5 Specific
- **URL:** https://github.com/nkanven/MT4-MT5-Trading-EA-Collections
- **Status:** ⚠️ Requires verification. Contact author for explicit permission before full integration.

## 7. Core Dependency License Report

| Name                | Version      | License                                            | Status    |
|---------------------|--------------|----------------------------------------------------|-----------|
| numpy               | 1.26.4       | BSD-3-Clause                                       | Allowed   |
| pandas              | 2.2.2        | BSD License                                        | Allowed   |
| torch               | 2.2.2        | BSD-3-Clause                                       | Allowed   |
| scikit-learn        | 1.4.2        | BSD-3-Clause                                       | Allowed   |
| stable-baselines3   | 2.3.2        | MIT                                                | Allowed   |
| transformers        | 4.40.1       | Apache 2.0                                         | Allowed   |
| sqlalchemy          | 2.0.30       | MIT                                                | Allowed   |
| fastapi             | 0.111.0      | MIT                                                | Allowed   |
| python-telegram-bot | 22.7         | LGPL-3.0-only                                      | Approved* |

*\*Note: LGPL is approved for use as a library. Proprietary SDKs (MetaApi, NVIDIA) are required for platform integration and are subject to their respective terms.*

---
**Last Updated**: 2024-Q1
**Owner**: Jules03 (Release Reliability & Governance)
