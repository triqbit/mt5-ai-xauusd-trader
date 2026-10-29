import datetime
from typing import Any, Dict, List

import feedparser
import yfinance as yf


class AtlasDataPipeline:
    @staticmethod
    def get_macro_yields() -> Dict[str, Any]:
        """Fetches 10-Year and 2-Year Treasury Yields using yfinance."""
        try:
            tnx = yf.Ticker("^TNX")
            hist = tnx.history(period="5d")
            latest_10y = hist['Close'].iloc[-1] if not hist.empty else None
            return {"10Y_Treasury_Yield": latest_10y}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_market_volatility() -> Dict[str, Any]:
        """Fetches VIX data."""
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="5d")
            latest_vix = hist['Close'].iloc[-1] if not hist.empty else None
            return {"VIX": latest_vix}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_forex_news() -> List[Dict[str, str]]:
        """Fetches recent financial news via a free RSS feed."""
        try:
            # Example using Yahoo Finance RSS for Gold
            feed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F")
            news = []
            for entry in feed.entries[:5]: # Top 5 recent headlines
                news.append({
                    "title": entry.title,
                    "published": entry.published
                })
            return news
        except Exception as e:
            return [{"error": str(e)}]

    @classmethod
    def aggregate_context(cls) -> Dict[str, Any]:
        return {
            "macro_data": {
                **cls.get_macro_yields(),
                **cls.get_market_volatility()
            },
            "news_data": cls.get_forex_news(),
            "timestamp": datetime.datetime.now().isoformat()
        }
