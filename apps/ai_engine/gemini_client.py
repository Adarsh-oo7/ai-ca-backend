import logging
from django.conf import settings
from google import genai
from google.genai import types
from google.genai.errors import APIError

logger = logging.getLogger('apps.ai_engine')

class GeminiClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set in settings.")
        
        # Initialize Google GenAI client
        self.client = genai.Client(api_key=self.api_key)
        self.model = settings.GEMINI_MODEL
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL
        self.dimensions = settings.GEMINI_EMBEDDING_DIMENSIONS

    def generate_text(self, prompt, system_instruction=None, temperature=None, max_output_tokens=None):
        """
        Generate text response from Gemini API.
        """
        if not self.api_key:
            return "Error: Gemini API key is missing. Please configure it in your settings."
            
        temp = temperature if temperature is not None else settings.GEMINI_TEMPERATURE
        max_tokens = max_output_tokens if max_output_tokens is not None else settings.GEMINI_MAX_TOKENS

        config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )
            return response.text
        except APIError as e:
            logger.error(f"Gemini API Error in generate_text: {e}")
            return f"Error communicating with Gemini: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in Gemini generate_text: {e}")
            return "An unexpected error occurred while generating the response."

    def get_embedding(self, text):
        """
        Generate a vector embedding using text-embedding-004.
        """
        if not self.api_key:
            logger.error("Gemini API key is missing for embeddings.")
            return None
            
        try:
            result = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=self.dimensions
                )
            )
            # Retrieve the embedding values
            embedding = result.embeddings[0].values
            return embedding
        except APIError as e:
            logger.error(f"Gemini API Error in get_embedding: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Gemini get_embedding: {e}")
            return None

    def generate_json(self, prompt, response_schema, system_instruction=None):
        """
        Generate structured JSON output conforming to a Pydantic schema or type description.
        """
        if not self.api_key:
            return None

        config = types.GenerateContentConfig(
            temperature=0.2, # Lower temperature for structured extraction
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating JSON with schema: {e}")
            return None
