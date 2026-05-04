# Runbook 07: Secret Rotation Procedure

## Overview
This runbook describes the procedure for rotating critical secrets and API credentials to maintain security hygiene or in response to a suspected leak. All rotation activities must be verified using the enterprise validation scripts.

## Scope of Sensitive Credentials
- `MT5_PASSWORD`: Trading account password.
- `METAAPI_TOKEN`: Cloud gateway authentication.
- `TELEGRAM_TOKEN`: Bot API access.
- `DATABASE_URL`: SQLAlchemy connection string (if using external DB).
- `DOCKER_PASSWORD`: Registry authentication for CI/CD.

## Rotation Schedule
- **Routine:** Every 90 days.
- **Emergency:** Immediately upon suspected compromise (e.g., Gitleaks CI failure).

## Step-by-Step Rotation

### 1. MT5 Password Rotation
1. Change the password in the Broker's client portal.
2. Update the `.env` file on the production server.
3. Validate the environment for placeholder detection: `python scripts/validate_env.py`.
4. Restart the bot: `docker restart mt5-trader`.

### 2. MetaAPI Token Rotation
1. Generate a new API token in the [MetaAPI Dashboard](https://app.metaapi.cloud/).
2. Update production `.env` with the new `METAAPI_TOKEN`.
3. Revoke the old token in the dashboard **after** the new one is verified.
4. Restart the bot.

### 3. Telegram Bot Token Rotation
1. Use the `/revoke` command with [@BotFather](https://t.me/botfather).
2. Copy the new token and update production `.env` (`TELEGRAM_TOKEN`).
3. Run `python scripts/validate_env.py` to ensure no placeholder tokens were used.
4. Restart the bot.

### 4. GitHub Actions Secrets Rotation
1. Navigate to **Settings > Secrets and variables > Actions**.
2. Update any modified secrets (e.g., `MT5_PASSWORD`, `TELEGRAM_TOKEN`).
3. Trigger a manual run of `ci.yml` or a `dry-run` release to verify the pipeline still passes.

## Verification & Validation
After any secret rotation, you **must** run the following to ensure the bot can still operate:

1. **Environment Consistency:**
   ```bash
   python scripts/validate_env.py
   ```
2. **Connectivity Check:**
   ```bash
   python scripts/doctor.py
   ```
3. **Health Status:**
   ```bash
   curl http://localhost:8000/health/readiness
   ```

## Safety Guidelines
- **Never** commit secrets or `.env` files to the repository.
- Always use `scripts/validate_env.py` to check for common placeholder strings (e.g., 'YOUR_TOKEN').
- Keep the old secret active for a 15-minute "grace period" if the service allows, to ensure the new one has propagated.

## Expected Outcomes
- New secrets are successfully applied and verified via `validate_env.py`.
- Application restarts and establishes connections with all services.
- Old secrets are revoked, minimizing the attack surface.

## Escalation Path
1. **Level 1:** Security Lead (@maintainer-quality).
2. **Level 2:** DevOps Lead (Jules03).
3. **Level 3:** Core Maintainer (@andonly1348).
