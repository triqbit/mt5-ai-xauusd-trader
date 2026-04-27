# License Compliance Policy

## Overview
This document outlines the license compliance policy for the MT5 AI/ML Trading Bot project. Our goal is to ensure that all software used and distributed as part of this project adheres to legal requirements and avoids licensing surprises.

## Allowed Licenses
The following licenses are generally permitted for use in this project:
- **MIT License**
- **Apache License 2.0**
- **BSD (2-Clause and 3-Clause)**
- **PSF (Python Software Foundation License)**
- **MPL 2.0 (Mozilla Public License)**
- **LGPL (v2.1, v3)** - *Permitted for library linking (e.g., psycopg2, python-telegram-bot)*
- **Proprietary/Other** - *Explicitly allowed for MetaAPI and NVIDIA SDKs required for core functionality*

## Disallowed Licenses
The following licenses are strictly prohibited as they may impose viral requirements or other incompatible conditions:
- **GPL (v2, v3)**
- **AGPL (v3)**
- **SSPL**

## Manual Review of "UNKNOWN" Licenses
- **TA-Lib:** Verified as BSD-like license. Allowed.
- **pandas-ta:** Verified as MIT license. Allowed.

## Automated License Scanning
License scanning is integrated into our CI/CD pipeline via GitHub Actions using `pip-licenses`. Every pull request and push to the main branch is scanned to ensure no disallowed licenses are introduced.

### Scanning Procedure
1. Dependencies are installed in a clean environment.
2. `pip-licenses` is executed to identify the license of every installed package.
3. The results are compared against our allow-list.
4. Any violation will fail the build and require immediate remediation.

## Attribution Requirements
All third-party components must be properly attributed in the `ATTRIBUTIONS.md` file located in the repository root.
- Each entry must include the component name, original author, license type, and a link to the source repository.
- For Apache 2.0 components, ensure the `NOTICE` file is respected and modifications are documented if required.

---

## Detailed Repository Audits (Integrated Components)

### 1. zero-was-here/tradingbot
- **License:** MIT
- **URL:** https://github.com/zero-was-here/tradingbot
- **Included Components:** PPO algorithm implementation, Dreamer V3 algorithm.
- **Status:** ✅ Compliant

### 2. ilahuerta-IA/mt5_live_trading_bot
- **License:** MIT
- **URL:** https://github.com/ilahuerta-IA/mt5_live_trading_bot
- **Included Components:** Ray Dalio portfolio allocation, 6-layer entry filter system.
- **Status:** ✅ Compliant

### 3. CodeDestroyer19/Neural-Network-MT5-Trading-Bot
- **License:** MIT
- **URL:** https://github.com/CodeDestroyer19/Neural-Network-MT5-Trading-Bot
- **Included Components:** Neural network architecture, Technical indicator calculations.
- **Status:** ✅ Compliant

### 4. AminHP/gym-mtsim
- **License:** MIT
- **URL:** https://github.com/AminHP/gym-mtsim
- **Included Components:** OpenAI Gym environment wrapper, MetaTrader 5 simulator.
- **Status:** ✅ Compliant

### 5. nguyenviettuan96/mt5_AI_trading_bot
- **License:** Apache 2.0
- **URL:** https://github.com/nguyenviettuan96/mt5_AI_trading_bot
- **Components:** LSTM neural network, Feature extraction pipeline.
- **Status:** ✅ Compliant

[Refer to docs/LICENSE_COMPLIANCE_ORIG.md for the full legacy audit list if needed]
