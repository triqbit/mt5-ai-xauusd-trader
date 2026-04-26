# 🗺️ Rollback Procedures

This document outlines the procedures for rolling back the **MT5 AI/ML Trading Bot** in case of deployment failures or production issues.

## 1. Code Rollback

Since this project uses Git for version control and GitHub Actions for CI/CD, the primary rollback mechanism is a Git revert.

### Procedure:
1. **Identify the stable commit:** Use \`git log\` to find the SHA of the last known stable commit.
2. **Revert to the stable version:**
   - Standard git revert of the merge commit.
   - Or reset to the stable commit.
3. **Verify CI:** Ensure the CI pipeline passes on the reverted version.

## 2. Configuration Rollback

If a failure is caused by an environment variable or \`.env\` file change:
1. Revert the changes in your environment management system (e.g., GitHub Secrets, Kubernetes ConfigMaps, or local \`.env\` file).
2. Restart the bot.

## 3. Database Rollback

If a deployment included database migrations (via Alembic):
1. **Identify the previous version:** \`alembic history\`
2. **Downgrade:**
   - Run \`alembic downgrade -1\`
3. **Verify:** Check database state.

## 4. Model Rollback

If a new model deployment causes performance degradation:
1. Restore the previous model weights from the \`models/trained/backup\` directory or your model registry.
2. Update the \`MODEL_PATH\` in your configuration.
3. Restart the bot.

---
**Atlas Guardian Directive:** Always verify system health using the Pre-flight Checks (\`python main.py --mode demo\`) after any rollback.
