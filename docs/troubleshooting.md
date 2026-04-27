# Troubleshooting Guide

Solutions for common issues encountered when setting up or running the MT5 AI Trading Bot.

## 1. MetaTrader 5 Connection Issues

### "Native mt5.initialize failed"
- **Cause**: MT5 terminal not installed at the path specified in `MT5_PATH`.
- **Solution**: Verify the path to `terminal64.exe` in your `.env` file.
- **Cause**: Incorrect Login, Password, or Server.
- **Solution**: Double-check credentials. Ensure you can log in manually to the MT5 desktop application.

### "No MetaTrader 5 SDK available on this platform"
- **Cause**: The `MetaTrader5` library only works on Windows.
- **Solution**: Use **MetaAPI** for Linux, Mac, or Docker deployments. Set `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID` in your `.env`.

## 2. Dependency Installation

### TA-Lib Installation Fails
- **Cause**: The TA-Lib Python wrapper requires the underlying C library.
- **Solution**:
    - **Windows**: Download the pre-compiled `.whl` from unofficial sources or build from source.
    - **Linux**: `wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz`, then `./configure` and `make install`.
    - **Mac**: `brew install ta-lib`.

### Torch/CUDA Issues
- **Cause**: Incompatible CUDA version for your GPU.
- **Solution**: Visit [pytorch.org](https://pytorch.org/) and follow the installation instructions specific to your OS and CUDA version.

## 3. Runtime Errors

### "Circuit breaker active: drawdown limit hit"
- **Cause**: The account has reached the maximum allowed drawdown (15% by default).
- **Solution**: Trading is halted to prevent further losses. Review your risk settings and model performance. Reset the state once the market regime has stabilized.

### "Daily loss limit reached"
- **Cause**: The bot has lost the maximum allowed percentage of equity for the current day.
- **Solution**: Wait for the next trading day (daily stats reset automatically).

## 4. Logging & Monitoring

### No Telegram Alerts
- **Cause**: Incorrect `TELEGRAM_TOKEN` or `TELEGRAM_CHAT_ID`.
- **Solution**: Verify your bot token with @BotFather and your Chat ID via @userinfobot. Ensure the bot is added to the target group.
