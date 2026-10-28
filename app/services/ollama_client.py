import json
import re
import time
from typing import Type, TypeVar, Tuple, Dict, Any, List, Optional
import httpx
from pydantic import BaseModel
from app.config import settings

T = TypeVar("T", bound=BaseModel)


class OllamaClientError(Exception):
    """Raised when Ollama request fails or Ollama is offline."""
    pass


class OllamaClient:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.REQUEST_TIMEOUT_SECONDS

    def get_client(self) -> httpx.Client:
        # Strictly local client with no external proxy routing
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            trust_env=False
        )

    def check_connection(self) -> Dict[str, Any]:
        """Checks if local Ollama daemon is reachable and lists available models."""
        try:
            with self.get_client() as client:
                res = client.get("/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    return {
                        "reachable": True,
                        "models": models,
                        "has_llm": any(settings.OLLAMA_LLM_MODEL in m for m in models),
                        "has_embed": any(settings.OLLAMA_EMBED_MODEL in m for m in models)
                    }
                return {
                    "reachable": False,
                    "error": f"Ollama HTTP {res.status_code}",
                    "models": [],
                    "has_llm": False,
                    "has_embed": False
                }
        except Exception as e:
            return {
                "reachable": False,
                "error": f"Cannot connect to local Ollama at {self.base_url}: {str(e)}",
                "models": [],
                "has_llm": False,
                "has_embed": False
            }

    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Generates embedding vector for a single text using local Ollama model."""
        embed_model = model or settings.OLLAMA_EMBED_MODEL
        try:
            with self.get_client() as client:
                # Preferred modern endpoint: /api/embed
                embed_payload = {"model": embed_model, "input": text}
                res = client.post("/api/embed", json=embed_payload)
                if res.status_code == 200:
                    data = res.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings and len(embeddings) > 0:
                        return embeddings[0]

                # Fallback to legacy endpoint: /api/embeddings
                legacy_payload = {"model": embed_model, "prompt": text}
                res = client.post("/api/embeddings", json=legacy_payload)
                if res.status_code == 200:
                    data = res.json()
                    embedding = data.get("embedding", [])
                    if embedding:
                        return embedding

                raise OllamaClientError(
                    f"Embedding failed (HTTP {res.status_code}): {res.text}"
                )
        except Exception as e:
            if isinstance(e, OllamaClientError):
                raise
            raise OllamaClientError(f"Error connecting to local Ollama for embeddings: {str(e)}")

    def get_embeddings_batch(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """Batch embedding generation with sequential fallback."""
        embed_model = model or settings.OLLAMA_EMBED_MODEL
        if not texts:
            return []
        try:
            with self.get_client() as client:
                res = client.post("/api/embed", json={"model": embed_model, "input": texts})
                if res.status_code == 200:
                    data = res.json()
                    embeddings = data.get("embeddings", [])
                    if len(embeddings) == len(texts):
                        return embeddings
        except Exception:
            pass

        # Sequential fallback if batch embedding is unsupported
        return [self.get_embedding(t, model=embed_model) for t in texts]

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        seed: int = 42,
        num_predict: int = 1024,
        response_format: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Sends chat completion request to local Ollama.
        Strict temperature 0, fixed seed, capped output tokens for deterministic output.
        """
        target_model = model or settings.OLLAMA_LLM_MODEL
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "seed": seed,
                "num_predict": num_predict
            }
        }
        if response_format is not None:
            payload["format"] = response_format

        start_time = time.perf_counter()
        try:
            with self.get_client() as client:
                res = client.post("/api/chat", json=payload)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                if res.status_code != 200:
                    raise OllamaClientError(
                        f"Ollama chat error (HTTP {res.status_code}): {res.text}"
                    )

                data = res.json()
                message_content = data.get("message", {}).get("content", "").strip()
                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)

                return {
                    "content": message_content,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "latency_ms": elapsed_ms,
                    "model": target_model
                }
        except Exception as e:
            if isinstance(e, OllamaClientError):
                raise
            raise OllamaClientError(f"Error calling local Ollama chat: {str(e)}")

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        schema_model: Optional[Type[T]] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        seed: int = 42,
        num_predict: int = 1024
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Requests JSON output from Ollama using schema format or "json".
        Parses and repairs output if needed.
        Returns (parsed_dict, metrics_dict).
        """
        format_spec: Any = "json"
        if schema_model is not None and hasattr(schema_model, "model_json_schema"):
            format_spec = schema_model.model_json_schema()

        raw_result = self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            seed=seed,
            num_predict=num_predict,
            response_format=format_spec
        )

        content = raw_result["content"]
        metrics = {
            "prompt_tokens": raw_result["prompt_tokens"],
            "completion_tokens": raw_result["completion_tokens"],
            "latency_ms": raw_result["latency_ms"],
            "model": raw_result["model"]
        }

        # Parse JSON from content (handling optional markdown fence blocks)
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            return parsed, metrics
        except json.JSONDecodeError:
            # Fallback regex extraction of outermost JSON object or list
            json_match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(0))
                    return parsed, metrics
                except json.JSONDecodeError:
                    pass

            raise OllamaClientError(f"Failed to parse model JSON output: {content[:200]}")


ollama_client = OllamaClient()
