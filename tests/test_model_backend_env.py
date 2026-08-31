from __future__ import annotations

import os
import tempfile
import unittest
import json
import subprocess
import urllib.error
from pathlib import Path
from unittest import mock

from evar.model_backend import OpenAIResponsesBackend, OpenRouterChatBackend, _load_env_api_key


class ModelBackendEnvTests(unittest.TestCase):
    def test_load_env_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text('OPENAI_API_KEY="test-key"\n', encoding="utf-8")

            self.assertEqual(_load_env_api_key(env_path), "test-key")

    def test_openai_backend_uses_dotenv_when_environment_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                with mock.patch.dict(os.environ, {}, clear=True):
                    backend = OpenAIResponsesBackend(model_name="test-model")
            finally:
                os.chdir(old_cwd)

        self.assertEqual(backend.api_key, "test-key")

    def test_openai_backend_sends_structured_output_schema(self) -> None:
        captured: dict[str, object] = {}

        class FakeHTTPResponse:
            def __enter__(self) -> "FakeHTTPResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"output_text":"{\\"ok\\":true}","usage":{"input_tokens":1,"output_tokens":2}}'

        def fake_urlopen(request: object, timeout: int) -> FakeHTTPResponse:
            del timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse()

        backend = OpenAIResponsesBackend(model_name="test-model", api_key="test-key")
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            response = backend.generate(
                "system",
                "user",
                response_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ok"],
                    "properties": {"ok": {"type": "boolean"}},
                },
            )

        payload = captured["payload"]
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(response.input_tokens, 1)
        self.assertEqual(response.output_tokens, 2)

    def test_openai_backend_omits_unsupported_optional_temperature(self) -> None:
        captured: dict[str, object] = {}

        class FakeHTTPResponse:
            def __enter__(self) -> "FakeHTTPResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"output_text":"{}","usage":{}}'

        def fake_urlopen(request: object, timeout: int) -> FakeHTTPResponse:
            del timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse()

        backend = OpenAIResponsesBackend(
            model_name="reasoning-model", temperature=None, api_key="test-key"
        )
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            backend.generate("system", "user")

        self.assertNotIn("temperature", captured["payload"])

    def test_openai_backend_sends_explicit_reasoning_effort(self) -> None:
        captured: dict[str, object] = {}

        class FakeHTTPResponse:
            def __enter__(self) -> "FakeHTTPResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"output_text":"{}","usage":{}}'

        def fake_urlopen(request: object, timeout: int) -> FakeHTTPResponse:
            del timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse()

        backend = OpenAIResponsesBackend(
            model_name="reasoning-model",
            temperature=None,
            reasoning_effort="none",
            api_key="test-key",
        )
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            backend.generate("system", "user")

        self.assertEqual(captured["payload"]["reasoning"], {"effort": "none"})

    def test_openrouter_backend_uses_dotenv_when_environment_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("OPENROUTER_API_KEY=test-router-key\n", encoding="utf-8")
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                with mock.patch.dict(os.environ, {}, clear=True):
                    backend = OpenRouterChatBackend(model_name="vendor/model")
            finally:
                os.chdir(old_cwd)

        self.assertEqual(backend.api_key, "test-router-key")

    def test_openrouter_backend_sends_structured_chat_request(self) -> None:
        captured: dict[str, object] = {}
        def fake_run(command: list[str], **kwargs: object) -> object:
            captured["timeout"] = kwargs["timeout"]
            captured["payload"] = json.loads(kwargs["input"].decode("utf-8"))
            return subprocess.CompletedProcess(command, 0, stdout=(
                b'{"model":"vendor/model","choices":[{"message":{"content":"{\\"ok\\":true}"}}],'
                b'"usage":{"prompt_tokens":3,"completion_tokens":4}}\n__EVAR_STATUS:200'
            ), stderr=b"")

        backend = OpenRouterChatBackend(
            model_name="vendor/model",
            max_output_tokens=1200,
            reasoning_effort="low",
            api_key="test-key",
        )
        with mock.patch("subprocess.run", fake_run):
            response = backend.generate(
                "system",
                "user",
                response_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ok"],
                    "properties": {"ok": {"type": "boolean"}},
                },
            )

        payload = captured["payload"]
        self.assertEqual(payload["model"], "vendor/model")
        self.assertEqual(payload["max_tokens"], 1200)
        self.assertEqual(payload["reasoning"], {"effort": "low"})
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])
        self.assertEqual(payload["provider"], {"require_parameters": True})
        self.assertEqual(captured["timeout"], 25)
        self.assertEqual(response.parsed_output, {"ok": True})
        self.assertEqual(response.input_tokens, 3)
        self.assertEqual(response.output_tokens, 4)

    def test_openrouter_retries_rate_limit_and_honors_retry_after(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def fake_run(command: list[str], **kwargs: object) -> object:
            del kwargs
            nonlocal calls
            calls += 1
            if calls == 1:
                return subprocess.CompletedProcess(command, 0, stdout=(
                    b'{"error":"busy"}\n__EVAR_STATUS:429'
                ), stderr=b"")
            return subprocess.CompletedProcess(command, 0, stdout=(
                b'{"choices":[{"message":{"content":"{}"}}],"usage":{}}\n__EVAR_STATUS:200'
            ), stderr=b"")

        backend = OpenRouterChatBackend(model_name="vendor/model", api_key="test-key")
        with mock.patch("subprocess.run", fake_run), mock.patch(
            "time.sleep", side_effect=lambda value: sleeps.append(value)
        ):
            response = backend.generate("system", "user")

        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [1.0])
        self.assertEqual(response.parsed_output, {})

    def test_openrouter_does_not_retry_payment_required(self) -> None:
        calls = 0

        def fake_run(command: list[str], **kwargs: object) -> object:
            del command, kwargs
            nonlocal calls
            calls += 1
            return subprocess.CompletedProcess([], 0, stdout=b'{"error":"payment"}\n__EVAR_STATUS:402', stderr=b"")

        backend = OpenRouterChatBackend(model_name="vendor/model", api_key="test-key")
        with mock.patch("subprocess.run", fake_run):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                backend.generate("system", "user")

        self.assertEqual(calls, 1)
        caught.exception.close()

    def test_openrouter_hard_deadline_is_positive(self) -> None:
        self.assertGreater(OpenRouterChatBackend.request_timeout_seconds, 0)
        self.assertGreaterEqual(OpenRouterChatBackend.max_total_seconds, OpenRouterChatBackend.request_timeout_seconds)
