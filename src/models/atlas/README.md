# ATLAS: Autonomous Trading Logic & Synthesis

This directory contains the ATLAS Multi-Agent architecture, integrating large language models (Vertex AI / Gemini) with quantitative strategies.

## Layers
*   **Layer 1: Macro Agents** (`layer1_macro.py`) - Evaluates FED policies and geopolitical news.
*   **Layer 4: Decision Agents** (`layer4_decision.py`) - CIO aggregates signals using a Darwinian engine; CRO monitors extreme risks.

## Integration
The `AtlasHybridSystem` in `integration.py` intercepts technical trading signals, requests macro analysis from the LLMs, and overrides or flattens trades if macroeconomic risks (like extreme VIX or contradictory news) are detected.

## Requirements
Ensure you have the following installed:
*   `google-cloud-aiplatform`
*   `feedparser`
*   `yfinance`

And appropriate Application Default Credentials (ADC) for Google Cloud Vertex AI set up in your environment.
