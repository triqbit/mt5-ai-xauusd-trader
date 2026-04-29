# License Compliance Policy & Tracking

## 1. Governance Policy

### 1.1 Overview
This policy defines the standards and procedures for managing open-source and third-party software licenses within the MT5 Trading Bot project. Our goal is to ensure legal compliance, minimize licensing risks, and maintain proper attribution for all integrated components.

### 1.2 License Categorization

#### 1.2.1 Allowed Licenses (Permissive)
The following licenses are generally approved for use in both internal code and external dependencies:
- **MIT**
- **Apache 2.0**
- **BSD (2-Clause and 3-Clause)**
- **PSF-2.0** (Python Software Foundation)
- **ISC**
- **Unlicense**
- **CC0** (Public Domain)

#### 1.2.2 Restricted Licenses
The following licenses are allowed **only** for external dependencies and must not be used for core project code:
- **LGPL** (Lesser General Public License)
- **MPL** (Mozilla Public License)

#### 1.2.3 Disallowed Licenses (Copyleft / Proprietary)
The following licenses are strictly prohibited as they may impose viral requirements or legal restrictions incompatible with our commercial or distribution goals:
- **GPL** (All versions)
- **AGPL** (Affero General Public License)
- **Proprietary / Commercial** (Unless explicitly approved by the Project Owner)

### 1.3 Attribution Requirements
All third-party code integrated into the repository must maintain its original copyright notices and license text.
- **Integrated Code:** Must retain original headers and a copy of the license in its respective directory.
- **External Dependencies:** Must be listed in `docs/DEPENDENCY_LICENSES.md` (generated automatically).
- **Project Credits:** All significant third-party integrations must be recorded in `ATTRIBUTIONS.md`.

### 1.4 Compliance Procedures

#### 1.4.1 Dependency Scanning
Every pull request triggers an automated license scan via GitHub Actions (`.github/workflows/license-check.yml`). This check:
- Identifies all installed Python dependencies.
- Compares their licenses against the approved list.
- Fails the build if a disallowed license is detected.

#### 1.4.2 Manual Integration Audit
Before merging code from another repository:
1. Verify the license is in the **Allowed** list.
2. Ensure the original license file is included.
3. Update `ATTRIBUTIONS.md` with the repository details and copyright info.

---

## 2. Integrated Component Tracking

### 2.1 MIT License Repositories (10 Total)

#### 1. zero-was-here/tradingbot
- **License:** MIT
- **URL:** https://github.com/zero-was-here/tradingbot
- **Copyright:** zero-was-here (2024)
- **Included Components:** PPO implementation, Dreamer V3, feature engineering.
- **Status:** ✅ Compliant

#### 2. ilahuerta-IA/mt5_live_trading_bot
- **License:** MIT
- **URL:** https://github.com/ilahuerta-IA/mt5_live_trading_bot
- **Copyright:** ilahuerta-IA (2024)
- **Included Components:** Risk management system, 6-layer filter, monitoring.
- **Status:** ✅ Compliant

#### 3. CodeDestroyer19/Neural-Network-MT5-Trading-Bot
- **License:** MIT
- **URL:** https://github.com/CodeDestroyer19/Neural-Network-MT5-Trading-Bot
- **Copyright:** CodeDestroyer19 (2023)
- **Included Components:** Neural network architecture, technical indicators.
- **Status:** ✅ Compliant

#### 4. AminHP/gym-mtsim
- **License:** MIT
- **URL:** https://github.com/AminHP/gym-mtsim
- **Copyright:** AminHP (2022)
- **Included Components:** MetaTrader 5 simulator, OpenAI Gym wrapper.
- **Status:** ✅ Compliant

#### 5. Stefodan21/Forex-trading-bot
- **License:** MIT
- **URL:** https://github.com/Stefodan21/Forex-trading-bot
- **Copyright:** Stefodan21 (2023)
- **Included Components:** PPO variant, GPU acceleration (DirectML).
- **Status:** ✅ Compliant

#### 6. geraked/metatrader5
- **License:** MIT
- **URL:** https://github.com/geraked/metatrader5
- **Copyright:** geraked (2023)
- **Included Components:** MQL5 strategies, Expert Advisor templates.
- **Status:** ✅ Compliant

### 2.2 Apache 2.0 License Repositories (2 Total)

#### nguyenviettuan96/mt5_AI_trading_bot
- **License:** Apache 2.0
- **URL:** https://github.com/nguyenviettuan96/mt5_AI_trading_bot
- **Copyright:** nguyenviettuan96 (2023)
- **Components:** LSTM neural network, RL integration.
- **Status:** ✅ Compliant

---

## 3. Risk Detection & Remediation
- **Unknown Licenses:** Any dependency with an "Unknown" or missing license must be manually investigated.
- **Incompatible Combinations:** Combining Apache 2.0 with GPLv2 is strictly avoided.
- **Remediation:** If a disallowed license is found, the component must be replaced with a compliant alternative or removed immediately.

---
*Version: 1.2*
*Owner: Jules03 (Release Reliability & Governance)*
