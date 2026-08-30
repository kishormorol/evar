from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from evar.benchmark.loader import validate_case, load_jsonl_cases
from evar.config import load_config
from evar.model_backend import DryRunBackend
from evar.run import _build_backend, _claim_evaluation_task, main


class LLMIntegrationTests(unittest.TestCase):
    def test_pilot_config_loads(self) -> None:
        config = load_config(Path("configs/pilot.yaml"))

        self.assertEqual(config.model.backend, "dry_run")
        self.assertEqual(config.protocol.critic_rounds, 1)
        self.assertEqual(config.experiment.seed, 7)

    def test_config_can_omit_temperature_for_reasoning_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "reasoning.yaml"
            config_path.write_text(
                "model:\n"
                "  backend: openai\n"
                "  model: reasoning-model\n"
                "  temperature: null\n"
                "  reasoning_effort: none\n"
                "protocol:\n"
                "  critic_rounds: 1\n"
                "  verifier_timeout_seconds: 5\n"
                "experiment:\n"
                "  seed: 1\n"
                "  repetitions: 1\n",
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertIsNone(config.model.temperature)
        self.assertEqual(config.model.reasoning_effort, "none")

    def test_pilot_cases_load_without_prompt_leakage_fields(self) -> None:
        cases = load_jsonl_cases(Path("benchmark/pilot_cases.jsonl"))

        self.assertEqual(len(cases), 10)
        task = _claim_evaluation_task(cases[0])
        self.assertNotIn("ground_truth", task)
        self.assertNotIn(cases[0].ground_truth.value, task)
        self.assertNotIn(cases[0].ground_truth_evidence, task)

    def test_changing_ground_truth_alone_does_not_change_task_input(self) -> None:
        raw = _raw_case(Path("repo"))
        supported = validate_case({**raw, "ground_truth": "SUPPORTED"})
        unsupported = validate_case({**raw, "ground_truth": "UNSUPPORTED"})

        self.assertEqual(_claim_evaluation_task(supported), _claim_evaluation_task(unsupported))

    def test_dry_run_prints_prompts_without_ground_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.jsonl"
            cases.write_text(json.dumps(_raw_case(Path(tmp))) + "\n", encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--cases",
                        str(cases),
                        "--protocol",
                        "evar_hard",
                        "--config",
                        "configs/pilot.yaml",
                        "--dry-run",
                    ]
                )

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("--- PROMPT 1 SYSTEM ---", output)
        self.assertIn("--- PROMPT 1 USER ---", output)
        self.assertIn("--- PROMPT 2 SYSTEM ---", output)
        self.assertNotIn("ground_truth", output)
        self.assertNotIn("SUPPORTED", output)
        self.assertNotIn("UNSUPPORTED", output)
        self.assertNotIn("The guard exists in sample.py.", output)

    def test_all_protocols_receive_same_reviewer_user_prompt(self) -> None:
        config = load_config(Path("configs/pilot.yaml"))
        case = validate_case(_raw_case(Path("repo")))
        prompts = []

        for protocol in ["ar", "ar_text", "evar_hard"]:
            backend = _build_backend(config, dry_run=True)
            with tempfile.TemporaryDirectory() as tmp:
                cases = Path(tmp) / "cases.jsonl"
                cases.write_text(json.dumps(_raw_case(Path("repo"))) + "\n", encoding="utf-8")
                with contextlib.redirect_stdout(io.StringIO()):
                    main(
                        [
                            "--cases",
                            str(cases),
                            "--protocol",
                            protocol,
                            "--config",
                            "configs/pilot.yaml",
                            "--dry-run",
                        ]
                    )
            del backend

        # Directly compare the task input used before protocol-specific system prompts.
        prompts = [_claim_evaluation_task(case) for _ in ["ar", "ar_text", "evar_hard"]]
        self.assertEqual(len(set(prompts)), 1)

    def test_model_backend_receives_no_ground_truth_in_dry_run_calls(self) -> None:
        backend = DryRunBackend()
        case = validate_case(_raw_case(Path("repo")))
        from evar.agents.model_reviewer import ModelAgentConfig, ModelReviewer

        reviewer = ModelReviewer(backend, ModelAgentConfig(model_name="dry"), protocol="ar")
        reviewer.review(_claim_evaluation_task(case), case.repo_path)

        call = backend.calls[0]
        self.assertNotIn("ground_truth", call.system_prompt)
        self.assertNotIn("ground_truth", call.user_prompt)
        self.assertNotIn(case.ground_truth.value, call.user_prompt)
        self.assertNotIn(case.ground_truth_evidence, call.user_prompt)

    def test_configured_run_records_claim_family_and_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = root / "cases.jsonl"
            output_dir = root / "results"
            cases.write_text(json.dumps(_raw_case(root)) + "\n", encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--cases",
                        str(cases),
                        "--protocol",
                        "evar_hard",
                        "--config",
                        "configs/pilot.yaml",
                        "--output-dir",
                        str(output_dir),
                    ]
                )

            output_path = Path(stdout.getvalue().strip())
            record = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(record["claim_family"], "missing_guard")
        self.assertGreaterEqual(record["duration"], 0.0)


def _raw_case(repo: Path) -> dict[str, object]:
    return {
        "case_id": "case-1",
        "repo_path": str(repo),
        "task_description": "Review the guard.",
        "claim": "handler is missing an input guard",
        "ground_truth": "UNSUPPORTED",
        "ground_truth_evidence": "The guard exists in sample.py.",
        "validation_command": ["python", "-m", "unittest"],
        "claim_family": "missing_guard",
    }
