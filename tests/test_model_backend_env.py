from __future__ import annotations

import os
import tempfile
import unittest
import json
from pathlib import Path
from unittest import mock

from evar.model_backend import OpenAIResponsesBackend, _load_env_api_key


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
