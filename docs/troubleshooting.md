# Troubleshooting

Common issues and their solutions.

## Connection Problems

- **MT5 not initialized**: Ensure the MT5 terminal is running and the path in `MT5_PATH` is correct. On Windows, MT5 must be installed and accessible.
- **Login failed**: Check your account number, password, and server. Ensure you have "AutoTrading" enabled in MT5 Options.
- **MetaAPI Fallback**: If running on Linux/Mac, ensure `METAAPI_TOKEN` is provided for cloud execution.

## Model Issues

- **Model file not found**: Ensure weights are placed in `models/trained/`. The default for ensemble is `ensemble_latest.pt`.
- **CUDA errors**: If `DEVICE=cuda` is used, ensure PyTorch is installed with GPU support and drivers are up to date.

## Database Errors

- **Connection Refused**: Check if your PostgreSQL/Redis instances are running and accessible from the bot's environment.
- **Migration errors**: If the schema changed, run `alembic upgrade head`.
