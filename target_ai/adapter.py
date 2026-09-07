"""
Target Adapter Module for QA-Safe.

Provides a common TargetAdapter interface and standardized TargetResponse
container to decouple campaign orchestration and evaluation from specific
target AI implementations. Includes NovaBotAdapter (local RAG) and
RESTTargetAdapter (generic HTTP API).
"""

from abc import ABC, abstractmethod
import json
import time
from typing import Any, Callable, Dict, List, Optional
import requests


class TargetResponse(dict):
    """
    Standardized response container for Target AI adapters.

    Inherits from dict to ensure 100% backward compatibility with
    isinstance(..., dict), .get(...), dictionary indexing, and serialization.
    """

    def __init__(
        self,
        target_response: str = "",
        retrieved_context: Optional[List[Any]] = None,
        visibility: Optional[List[str]] = None,
        raw_response: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        context_list = retrieved_context if retrieved_context is not None else []
        vis_list = visibility if visibility is not None else []
        meta_dict = metadata if metadata is not None else {}

        data = {
            "target_response": target_response,
            "retrieved_context": context_list,
            "visibility": vis_list,
            "raw_response": raw_response,
            "metadata": meta_dict,
            **kwargs,
        }
        super().__init__(data)

    @property
    def target_response(self) -> str:
        return self.get("target_response", "")

    @property
    def retrieved_context(self) -> List[Any]:
        return self.get("retrieved_context", [])

    @property
    def visibility(self) -> List[str]:
        return self.get("visibility", [])

    @property
    def raw_response(self) -> Any:
        return self.get("raw_response")

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.get("metadata", {})


class TargetAdapter(ABC):
    """
    Abstract base class defining the common interface for Target AI systems in QA-Safe.
    """

    def __init__(self, name: str = "TargetAdapter") -> None:
        self.name = name

    @abstractmethod
    def send_prompt(self, prompt: str, **kwargs: Any) -> TargetResponse:
        """
        Sends a prompt to the target system and returns a standardized TargetResponse.
        """
        pass

    def generate_response(
        self, prompt: str, test_mode: bool = True, **kwargs: Any
    ) -> TargetResponse | str:
        """
        Backward-compatibility method matching the legacy TargetAI signature.
        """
        response = self.send_prompt(prompt, **kwargs)
        if test_mode:
            return response
        return response.target_response

    def get_response(
        self, prompt: str, test_mode: bool = False, **kwargs: Any
    ) -> TargetResponse | str:
        """
        Backward-compatibility method matching the legacy ask_target_bot / get_response signature.
        """
        response = self.send_prompt(prompt, **kwargs)
        if test_mode:
            return response
        return response.target_response

    def __call__(
        self, prompt: str, test_mode: bool = True, **kwargs: Any
    ) -> TargetResponse | str:
        """
        Callable interface matching legacy TargetAI invocations.
        """
        return self.generate_response(prompt, test_mode=test_mode, **kwargs)


class NovaBotAdapter(TargetAdapter):
    """
    Adapter wrapping the existing local NovaBot RAG assistant.
    Delegates to the existing TargetAI / ask_target_bot implementation without modifying it.
    """

    def __init__(
        self,
        model_name: str = "NovaBot (gemma3:1b)",
        target_ai: Optional[Any] = None,
    ) -> None:
        super().__init__(name=model_name)
        if target_ai is not None:
            self.target_ai = target_ai
        else:
            from .target_bot import TargetAI

            self.target_ai = TargetAI(model_name=model_name)

    def send_prompt(self, prompt: str, **kwargs: Any) -> TargetResponse:
        """
        Executes prompt against NovaBot with RAG retrieval enabled (test_mode=True).
        """
        raw_output = self.target_ai.generate_response(prompt, test_mode=True)
        if isinstance(raw_output, dict):
            return TargetResponse(
                target_response=raw_output.get("target_response", ""),
                retrieved_context=raw_output.get("retrieved_context", []),
                visibility=raw_output.get("visibility", []),
                raw_response=raw_output,
                metadata={"model_name": self.name},
            )
        return TargetResponse(
            target_response=str(raw_output or ""),
            retrieved_context=[],
            visibility=[],
            raw_response=raw_output,
            metadata={"model_name": self.name},
        )


class RESTTargetAdapter(TargetAdapter):
    """
    Generic HTTP REST adapter to evaluate external AI systems exposed via an HTTP API.
    """

    DEFAULT_CANDIDATE_KEYS = [
        "target_response",
        "response",
        "output",
        "text",
        "content",
        "answer",
        "message",
    ]

    def __init__(
        self,
        endpoint_url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        prompt_field: str = "prompt",
        payload_template: Optional[Any] = None,
        response_field: Optional[str] = None,
        response_extractor: Optional[Callable[[Any], str]] = None,
        name: str = "RESTTargetAdapter",
        session: Optional[requests.Session] = None,
    ) -> None:
        """
        Args:
            endpoint_url: Complete HTTP(S) URL of the target API endpoint.
            method: HTTP method (POST, GET, etc.). Defaults to 'POST'.
            headers: Optional HTTP headers dictionary (e.g., {'Authorization': 'Bearer ...'}).
            timeout: Request timeout in seconds. Defaults to 30.0.
            prompt_field: Top-level JSON payload key for prompt if no template is provided.
            payload_template: Dict/List/Callable defining custom request payload structure.
            response_field: Dot-separated JSON path to target text (e.g., 'choices.0.message.content').
            response_extractor: Callable function taking parsed JSON and returning response string.
            name: Human-readable identifier for reporting.
            session: Optional custom requests.Session instance for connection pooling.
        """
        super().__init__(name=name)
        self.endpoint_url = endpoint_url
        self.method = method.upper()
        self.headers = headers if headers is not None else {"Content-Type": "application/json"}
        self.timeout = timeout
        self.prompt_field = prompt_field
        self.payload_template = payload_template
        self.response_field = response_field
        self.response_extractor = response_extractor
        self.session = session if session is not None else requests.Session()

    def _build_payload(self, prompt: str) -> Any:
        if callable(self.payload_template):
            return self.payload_template(prompt)
        elif isinstance(self.payload_template, dict):
            return self._format_template(self.payload_template, prompt)
        elif isinstance(self.payload_template, list):
            return [self._format_template(item, prompt) for item in self.payload_template]
        return {self.prompt_field: prompt}

    def _format_template(self, template: Any, prompt: str) -> Any:
        if isinstance(template, str):
            return template.replace("{prompt}", prompt)
        elif isinstance(template, dict):
            return {k: self._format_template(v, prompt) for k, v in template.items()}
        elif isinstance(template, list):
            return [self._format_template(item, prompt) for item in template]
        return template

    def _extract_nested_field(self, data: Any, field_path: str) -> Any:
        parts = field_path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None
            if current is None:
                return None
        return current

    def _extract_response_text(self, data: Any) -> tuple[str, Optional[str]]:
        # 1. Custom extractor callable
        if callable(self.response_extractor):
            try:
                extracted = self.response_extractor(data)
                if extracted is not None:
                    return str(extracted), None
                return "", "response_extractor returned None"
            except Exception as e:
                return "", f"response_extractor raised error: {e}"

        # 2. Configured dot-path field
        if self.response_field:
            val = self._extract_nested_field(data, self.response_field)
            if val is not None:
                return str(val), None
            return "", f"Configured response_field '{self.response_field}' not found in response"

        # 3. String payload
        if isinstance(data, str):
            return data, None

        # 4. Dictionary inspection
        if isinstance(data, dict):
            # Check direct candidate keys
            for key in self.DEFAULT_CANDIDATE_KEYS:
                if key in data and data[key] is not None:
                    val = data[key]
                    if isinstance(val, dict) and "content" in val:
                        return str(val["content"]), None
                    return str(val), None

            # Check OpenAI / Ollama style choices structure
            choices = data.get("choices")
            if isinstance(choices, list) and len(choices) > 0:
                choice = choices[0]
                if isinstance(choice, dict):
                    if "message" in choice and isinstance(choice["message"], dict):
                        content = choice["message"].get("content")
                        if content is not None:
                            return str(content), None
                    if "text" in choice and choice["text"] is not None:
                        return str(choice["text"]), None

        return "", "Could not locate text response in API payload"

    def send_prompt(self, prompt: str, **kwargs: Any) -> TargetResponse:
        """
        Sends the test prompt to the external REST API and returns a normalized TargetResponse.
        Catches network, HTTP, JSON decoding, and schema errors without crashing the campaign.
        """
        start_time = time.time()
        payload = self._build_payload(prompt)

        req_kwargs: Dict[str, Any] = {
            "headers": self.headers,
            "timeout": self.timeout,
            **kwargs,
        }

        if self.method == "GET":
            req_kwargs["params"] = payload
        else:
            req_kwargs["json"] = payload

        try:
            response = self.session.request(
                method=self.method,
                url=self.endpoint_url,
                **req_kwargs,
            )
            latency_ms = round((time.time() - start_time) * 1000.0, 2)

            # Check HTTP status error
            if response.status_code >= 400:
                return TargetResponse(
                    target_response="",
                    retrieved_context=[],
                    visibility=[],
                    raw_response=response.text,
                    metadata={
                        "endpoint_url": self.endpoint_url,
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                        "error_type": "HTTPError",
                        "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    },
                )

            # Parse JSON
            try:
                data = response.json()
            except (ValueError, json.JSONDecodeError) as json_err:
                return TargetResponse(
                    target_response="",
                    retrieved_context=[],
                    visibility=[],
                    raw_response=response.text,
                    metadata={
                        "endpoint_url": self.endpoint_url,
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                        "error_type": "JSONDecodeError",
                        "error": f"Invalid JSON response: {json_err}",
                    },
                )

            # Extract response text
            extracted_text, extract_err = self._extract_response_text(data)

            if extract_err:
                return TargetResponse(
                    target_response="",
                    retrieved_context=[],
                    visibility=[],
                    raw_response=data,
                    metadata={
                        "endpoint_url": self.endpoint_url,
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                        "error_type": "MissingField",
                        "error": extract_err,
                    },
                )

            return TargetResponse(
                target_response=extracted_text,
                retrieved_context=[],
                visibility=[],
                raw_response=data,
                metadata={
                    "endpoint_url": self.endpoint_url,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                },
            )

        except requests.exceptions.Timeout as timeout_err:
            latency_ms = round((time.time() - start_time) * 1000.0, 2)
            return TargetResponse(
                target_response="",
                retrieved_context=[],
                visibility=[],
                raw_response=None,
                metadata={
                    "endpoint_url": self.endpoint_url,
                    "latency_ms": latency_ms,
                    "error_type": "Timeout",
                    "error": f"Request timed out after {self.timeout}s: {timeout_err}",
                },
            )

        except requests.exceptions.ConnectionError as conn_err:
            latency_ms = round((time.time() - start_time) * 1000.0, 2)
            return TargetResponse(
                target_response="",
                retrieved_context=[],
                visibility=[],
                raw_response=None,
                metadata={
                    "endpoint_url": self.endpoint_url,
                    "latency_ms": latency_ms,
                    "error_type": "ConnectionError",
                    "error": f"Connection error to {self.endpoint_url}: {conn_err}",
                },
            )

        except Exception as err:
            latency_ms = round((time.time() - start_time) * 1000.0, 2)
            return TargetResponse(
                target_response="",
                retrieved_context=[],
                visibility=[],
                raw_response=None,
                metadata={
                    "endpoint_url": self.endpoint_url,
                    "latency_ms": latency_ms,
                    "error_type": type(err).__name__,
                    "error": str(err),
                },
            )
