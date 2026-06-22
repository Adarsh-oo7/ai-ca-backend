import logging
import time
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
        Includes automatic retry for temporary 503 Service Unavailable errors.
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

        max_retries = 3
        delay = 1.0

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                )
                return response.text
            except APIError as e:
                # 503 indicates service unavailable/overloaded
                if e.code == 503 and attempt < max_retries - 1:
                    logger.warning(f"Gemini API 503 (Unavailable) on attempt {attempt+1}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.error(f"Gemini API Error in generate_text: {e}")
                return f"Error communicating with Gemini: {str(e)}"
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Gemini API 503 Exception on attempt {attempt+1}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.error(f"Unexpected error in Gemini generate_text: {e}")
                return "An unexpected error occurred while generating the response."

    def get_embedding(self, text):
        """
        Generate a vector embedding using text-embedding-004.
        Includes automatic retry for temporary 503 errors.
        """
        if not self.api_key:
            logger.error("Gemini API key is missing for embeddings.")
            return None
            
        max_retries = 3
        delay = 1.0

        for attempt in range(max_retries):
            try:
                result = self.client.models.embed_content(
                    model=self.embedding_model,
                    contents=text,
                    config=types.EmbedContentConfig(
                        output_dimensionality=self.dimensions
                    )
                )
                return result.embeddings[0].values
            except APIError as e:
                if e.code == 503 and attempt < max_retries - 1:
                    logger.warning(f"Gemini Embeddings API 503 on attempt {attempt+1}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.error(f"Gemini API Error in get_embedding: {e}")
                return None
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Gemini Embeddings 503 Exception on attempt {attempt+1}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.error(f"Unexpected error in Gemini get_embedding: {e}")
                return None

    def generate_json(self, prompt, response_schema, system_instruction=None):
        """
        Generate structured JSON output conforming to a Pydantic schema or type description.
        Includes automatic retry for temporary 503 errors.
        """
        if not self.api_key:
            return None

        config = types.GenerateContentConfig(
            temperature=0.2, # Lower temperature for structured extraction
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema
        )

        max_retries = 3
        delay = 1.0

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                )
                return response.text
            except APIError as e:
                if e.code == 503 and attempt < max_retries - 1:
                    logger.warning(f"Gemini JSON API 503 on attempt {attempt+1}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.error(f"Error generating JSON with schema: {e}")
                return None
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Gemini JSON 503 Exception on attempt {attempt+1}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.error(f"Unexpected error in Gemini generate_json: {e}")
                return None

    def generate_audio(self, text, voice_name="Charon"):
        """
        Generate audio output (speech) from Gemini API using the specified voice.
        Returns a tuple of (audio_bytes, mime_type).
        """
        if not self.api_key:
            logger.error("Gemini API key is missing for audio generation.")
            return None, None

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )

        max_retries = 3
        delay = 1.0

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=text,
                    config=config
                )
                
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        data = part.inline_data.data
                        mime_type = part.inline_data.mime_type or "audio/wav"
                        if isinstance(data, str):
                            import base64
                            data = base64.b64decode(data)
                        return data, mime_type
                
                logger.error("No audio content generated in Gemini response.")
                return None, None
            except APIError as e:
                if e.code == 503 and attempt < max_retries - 1:
                    logger.warning(f"Gemini API 503 on audio attempt {attempt+1}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.error(f"Gemini API Error in generate_audio: {e}")
                return None, None
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Gemini 503 Exception on audio attempt {attempt+1}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.error(f"Unexpected error in Gemini generate_audio: {e}")
                return None, None
