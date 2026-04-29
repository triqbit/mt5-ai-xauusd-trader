# Runbook 05: Failed Deployment Rollback

## Description
This runbook defines the process for rolling back a failed deployment to a known stable state, covering both Docker containers and Git-based code versions.

## Failure Scenarios

### 1. Failed Docker Deployment
**Symptoms:** New container fails to start, crash loops, or shows critical errors in logs after an update.
**Cause:** Regression in code, missing environment variables, or dependency issues in the Docker image.

**Steps to Recover:**
1.  **Identify the previous stable tag:** Look at the CI/CD history or Docker registry for the previous successful image tag (e.g., `triqbit/mt5-ai-xauusd-trader:stable`).
2.  **Stop the failing container:**
    ```bash
    docker stop trading-bot
    docker rm trading-bot
    ```
3.  **Run the previous stable image:**
    ```bash
    docker run -d --name trading-bot --env-file .env triqbit/mt5-ai-xauusd-trader:<PREVIOUS_STABLE_TAG>
    ```
4.  **Verify logs:**
    ```bash
    docker logs -f trading-bot
    ```

---

### 2. Failed Code Deployment (Manual/Git)
**Symptoms:** Application logic is broken after a `git pull` or manual update.
**Cause:** Bugs introduced in the latest merge.

**Steps to Recover:**
1.  **Identify the last stable commit:**
    ```bash
    git log --oneline -n 10
    ```
2.  **Hard reset to the stable commit:**
    ```bash
    # Replace <COMMIT_HASH> with the actual hash
    git reset --hard <COMMIT_HASH>
    ```
3.  **Restart the application:**
    ```bash
    python main.py --mode demo
    ```
4.  **Verify functionality:** Ensure the bot starts and initializes connectors without error.

---

## Escalation Path
- **Deployment Strategy Failure:** Escalate to the Release Engineering Lead (Jules03).
- **Persistent Critical Bug:** Escalate to the Technical Lead (Jules01) for emergency hotfix.

## Verification Commands
1. Check running container version:
   ```bash
   docker ps --format "{{.Image}}"
   ```
2. Check current Git commit:
   ```bash
   git rev-parse HEAD
   ```
3. Check application logs for startup success:
   ```bash
   grep "initialised" logs/trading.log
   ```
