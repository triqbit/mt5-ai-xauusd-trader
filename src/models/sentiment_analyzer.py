"""
Sentiment Analyzer Module
Analyzes market sentiment using financial news or social media signals.
"""
import logging
from typing import Dict


class SentimentAnalyzer:
    """
    Analyzes market sentiment for symbols.
    In a production environment, this would integrate with an LLM (FinBERT)
    or a News API (e.g., AlphaVantage, NewsAPI).
    """

    def __init__(self, model_name: str = "ProsusAI/finbert"):
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self._initialized = False
        self.tokenizer = None
        self.model = None

    def initialize(self):
        """Lazily initialize the ML model."""
        if self._initialized:
            return

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self._initialized = True
            self.logger.info(f"Sentiment model {self.model_name} initialized.")
        except ImportError:
            self.logger.warning("Transformers not installed. Sentiment model skipped.")
        except Exception as e:
            self.logger.error(f"Failed to initialize sentiment model: {e}")

    def get_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of a given text.
        Returns probabilities for [positive, negative, neutral].
        """
        if not self._initialized:
            self.initialize()

        if not self._initialized:
            return {"positive": 0.33, "negative": 0.33, "neutral": 0.34}

        try:
            import torch

            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            # FinBERT labels: 0: positive, 1: negative, 2: neutral
            p = probs[0].tolist()
            return {"positive": p[0], "negative": p[1], "neutral": p[2]}
        except Exception as e:
            self.logger.error(f"Sentiment analysis failed: {e}")
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}

    def get_symbol_sentiment(self, symbol: str) -> float:
        """
        Aggregate sentiment score for a symbol (-1.0 to 1.0).
        Placeholder for real news aggregation logic.
        """
        # In reality, fetch recent headlines for the symbol here.
        dummy_headlines = [
            "Gold prices steady as investors await inflation data",
            "XAUUSD faces resistance near multi-month highs",
        ]

        scores = []
        for text in dummy_headlines:
            res = self.get_sentiment(text)
            score = res["positive"] - res["negative"]
            scores.append(score)

        return sum(scores) / len(scores) if scores else 0.0


__all__ = ["SentimentAnalyzer"]
