"""
Vertex AI Client Wrapper
Connects to Google Cloud Vertex AI using Application Default Credentials.
"""

import os

import structlog
import vertexai
from vertexai.generative_models import GenerativeModel

logger = structlog.get_logger(__name__)

class VertexClient:
    def __init__(self, project_id: str | None = None, location: str = "us-central1", model_name: str = "gemini-1.5-pro-preview-0409"):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self.model_name = model_name

        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(self.model_name)
            logger.info("Vertex AI Client initialized successfully.", project=self.project_id)
        except Exception as e:
            logger.error("Failed to initialize Vertex AI client.", error=str(e))
            self.model = None

    def query(self, prompt: str, temperature: float = 0.2) -> str:
        """Sends a query to the Vertex AI model."""
        if not self.model:
            return "ERROR: Vertex AI Client not initialized."

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"temperature": temperature}
            )
            return response.text
        except Exception as e:
            logger.error("Vertex AI query failed.", error=str(e))
            return f"ERROR: {e!s}"
