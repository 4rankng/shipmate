import fcntl
import csv
import io
import contextlib
import json
import os
import stat
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import run_metrics


class RunMetricsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "runs"

    def tearDown(self):
        self.temp_dir.cleanup()

    def start(self, *, mode="run", source_kind="jira", work_item="RGPAYM-42"):
        return run_metrics.start_record(
            mode=mode,
            repository=Path("/tmp/example-repository"),
            work_item=work_item,
            source_kind=source_kind,
            engineer_id=None,
            native_run_id="native-1",
            output_dir=self.output_dir,
            now="2026-09-16T01:00:00Z",
        )

    def test_legacy_metrics_remain_readable_and_resumable_after_rename(self):
        self.assertEqual(run_metrics.DEFAULT_OUTPUT_DIR, Path.home() / '.local/state/l3-workflow/runs')
        path = self.start()
        record = run_metrics.load_record(path)
        record['harness']['name'] = 'L3 SDLC'
        record['harness']['version'] = '3.8.7'
        path.write_text(json.dumps(record))
        original = path.read_bytes()
        loaded = run_metrics.load_record(path)
        self.assertEqual(path.read_bytes(), original)
        paused = run_metrics.checkpoint_record(path, 'needs-input', next_action='Choose retention')
        self.assertEqual(paused['run_id'], loaded['run_id'])
        self.assertEqual(paused['harness'], loaded['harness'])
        self.assertEqual(len(run_metrics.export_rows(self.output_dir)), 1)

    def update(self, path, revision, values, *, now="2026-09-16T01:05:00Z"):
        return run_metrics.update_record(
            path,
            {"expected_revision": revision, "set": values},
            now=now,
        )

    def test_checkpoint_pause_resume_preserves_identity_and_does_not_stop(self):
        path = self.start()
        original = run_metrics.load_record(path)
        paused = run_metrics.checkpoint_record(
            path, "needs-input", next_action="Choose retention",
            now="2026-09-16T01:05:00Z",
        )
        self.assertEqual(paused["run"]["status"], "running")
        self.assertIsNone(paused["run"]["stopped_at"])
        resumed = run_metrics.checkpoint_record(path, "running", now="2026-09-16T01:06:00Z")
        self.assertEqual(resumed["run_id"], original["run_id"])
        self.assertIsNone(resumed["measurement_notes"]["l3"]["next_action"])
        self.assertEqual(resumed["measurement_notes"]["l3"]["revision"], 2)

    def test_checkpoint_mr_handoff_and_completion_are_consistent(self):
        path = self.start()
        with self.assertRaisesRegex(ValueError, "initial MR"):
            run_metrics.checkpoint_record(path, "completed")
        record = run_metrics.checkpoint_record(
            path, "verification-pending", mr_url="https://gitlab.example/mr/1",
            mr_sha="abc", mr_created_at="2026-09-16T01:04:00Z",
            now="2026-09-16T01:05:00Z",
        )
        self.assertEqual(record["run"]["status"], "mr_created")
        self.assertIsNone(record["run"]["stopped_at"])
        self.assertEqual(run_metrics.export_rows(self.output_dir)[0]["invocation_to_mr_minutes"], 4)
        completed = run_metrics.checkpoint_record(path, "completed", now="2026-09-16T01:10:00Z")
        retried = run_metrics.checkpoint_record(path, "completed", now="2026-09-16T01:12:00Z")
        self.assertEqual(completed["run"]["stopped_at"], "2026-09-16T01:10:00Z")
        self.assertEqual(retried["run"]["stopped_at"], completed["run"]["stopped_at"])
        self.assertEqual(completed["timing"]["elapsed_to_stop_minutes"], 10)
        with self.assertRaises(ValueError):
            run_metrics.checkpoint_record(
                path, "running", mr_url="https://gitlab.example/mr/2",
                mr_sha="other", mr_created_at="2026-09-16T01:11:00Z",
                now="2026-09-16T01:12:00Z",
            )

    def test_checkpoint_standalone_and_failed_runs_need_no_mr(self):
        for mode in ("specify", "review"):
            path = self.start(mode=mode)
            record = run_metrics.checkpoint_record(path, "completed", now="2026-09-16T01:05:00Z")
            self.assertIsNone(record["outcome"]["classification"])
            self.assertEqual(record["timing"]["elapsed_to_stop_minutes"], 5)
        path = self.start()
        record = run_metrics.checkpoint_record(
            path, "stopped", end_status="failed", next_action="Fix test failure",
            now="2026-09-16T01:05:00Z",
        )
        self.assertEqual(record["outcome"]["classification"], "no_mr")
        self.assertEqual(record["run"]["status"], "failed")
        retried = run_metrics.checkpoint_record(path, "stopped", now="2026-09-16T01:06:00Z")
        self.assertEqual(retried["run"]["status"], "failed")
        self.assertEqual(retried["run"]["stopped_at"], record["run"]["stopped_at"])

    def test_checkpoint_rejects_partial_mr_and_invalid_status_without_writing(self):
        path = self.start()
        before = path.read_bytes()
        for kwargs in (
            {"status": "completed", "mr_url": "https://gitlab.example/mr/1"},
            {"status": "completed", "end_status": "failed"},
            {"status": "not-a-status"},
            {"status": "stopped", "end_status": "invented"},
            {"status": "running", "mr_url": "https://gitlab.example/mr/1",
             "mr_sha": "abc", "mr_created_at": "2099-01-01T00:00:00Z"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_metrics.checkpoint_record(path, **kwargs)
            self.assertEqual(path.read_bytes(), before)

    def test_export_preserves_unknowns_zero_modes_and_attempts(self):
        first = self.start()
        self.update(first, 0, {"/plan_revisions/autonomous": 0})
        self.start()
        self.start(mode="specify", source_kind="chat", work_item=None)
        rows = run_metrics.export_rows(self.output_dir)
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({row["run_id"] for row in rows}), 3)
        row = next(row for row in rows if row["run_id"] == first.stem)
        self.assertIsNone(row["human_minutes_before_mr"])
        self.assertIsNone(row["generation_input_tokens"])
        self.assertEqual(row["autonomous_plan_revisions"], 0)
        self.assertIn("/human_effort/before_mr_or_stop_active_minutes", row["missing_reasons"])
        self.assertEqual(len(run_metrics.export_rows(self.output_dir, mode="run")), 2)
        self.assertEqual(len(run_metrics.export_rows(self.output_dir, work_item="RGPAYM-42")), 2)
        self.assertEqual(run_metrics.export_rows(self.output_dir, since="2026-09-17T00:00:00Z"), [])
        self.assertEqual(run_metrics.export_rows(self.output_dir, before="2026-09-16T01:00:00Z"), [])

    def test_export_rejects_corrupt_duplicate_and_symlink_records(self):
        path = self.start()
        other = self.output_dir / "copy.json"
        other.write_bytes(path.read_bytes())
        with self.assertRaisesRegex(ValueError, "duplicate run_id"):
            run_metrics.export_rows(self.output_dir)
        other.unlink()
        other.symlink_to(path)
        with self.assertRaises(OSError):
            run_metrics.export_rows(self.output_dir)
        other.unlink()
        other.write_text("{invalid")
        with self.assertRaises(ValueError):
            run_metrics.export_rows(self.output_dir)
        with self.assertRaises(FileNotFoundError):
            run_metrics.export_rows(self.output_dir / "missing")

    def test_export_cli_csv_and_json_roundtrip_and_formula_safety(self):
        path = self.start(work_item="=malicious()")
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(run_metrics.run([
                "export", "--input-dir", str(self.output_dir), "--format", "csv",
            ]), 0)
        rows = list(csv.DictReader(io.StringIO(captured.getvalue())))
        self.assertEqual(rows[0]["work_item"], "'=malicious()")
        self.assertEqual(rows[0]["human_minutes_before_mr"], "")
        self.assertEqual(rows[0]["run_id"], path.stem)
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            run_metrics.run(["export", "--input-dir", str(self.output_dir), "--format", "json"])
        self.assertEqual(json.loads(captured.getvalue())[0]["work_item"], "=malicious()")

    def test_checkpoint_cli_records_terminal_time(self):
        path = self.start(mode="specify")
        with contextlib.redirect_stdout(io.StringIO()):
            run_metrics.run(["checkpoint", str(path), "--status", "completed"])
        self.assertEqual(run_metrics.load_record(path)["measurement_notes"]["l3"]["workflow_status"],
                         "completed")

    def test_export_empty_filters_and_formula_prefixes(self):
        self.output_dir.mkdir()
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            run_metrics.run(["export", "--input-dir", str(self.output_dir)])
        self.assertEqual(captured.getvalue().splitlines()[0].split(","), run_metrics.EXPORT_COLUMNS)
        for value in ("=SUM(1)", " +1", "-1", "@formula", "\ttext", "\rtext", "\ntext"):
            self.assertEqual(run_metrics._csv_value(value), "'" + value)
        self.assertEqual(run_metrics._csv_value(0), 0)
        for kwargs in ({"mode": "unknown"}, {"since": "yesterday"},
                       {"since": "2026-09-17T00:00:00Z", "before": "2026-09-16T00:00:00Z"}):
            with self.assertRaises(ValueError):
                run_metrics.export_rows(self.output_dir, **kwargs)

    def test_export_existing_mr_does_not_invent_negative_creation_time(self):
        path = self.start(mode="review")
        run_metrics.checkpoint_record(
            path, "completed", mr_url="https://gitlab.example/mr/1", mr_sha="abc",
            mr_created_at="2026-09-15T01:00:00Z", now="2026-09-16T01:05:00Z",
        )
        row = run_metrics.export_rows(self.output_dir)[0]
        self.assertIsNone(row["invocation_to_mr_minutes"])
        self.assertEqual(row["missing_reasons"]["/export/invocation_to_mr_minutes"],
                         "MR predates this invocation")

    def test_checkpoint_obeys_revision_conflict(self):
        path = self.start(mode="specify")
        original = run_metrics.update_record

        def competing_update(path, patch, now=None):
            original(path, {"expected_revision": 0, "set": {"/plan_revisions/autonomous": 1}})
            return original(path, patch, now=now)

        with patch.object(run_metrics, "update_record", side_effect=competing_update):
            with self.assertRaises(run_metrics.RevisionConflict):
                run_metrics.checkpoint_record(path, "completed")
        self.assertIsNone(run_metrics.load_record(path)["run"]["stopped_at"])

    def test_normal_run_derives_classification_timing_and_private_file(self):
        path = self.start()
        record = run_metrics.load_record(path)
        self.assertEqual(record["schema_version"], "l3-run-metrics/1.0")
        self.assertEqual(record["metric_source"], {
            "page_id": 2233074585, "page_version": 17, "attachment_version": 3,
        })
        uuid.UUID(record["run_id"])
        self.assertEqual(record["harness"]["name"], "Shipmate")
        manifest = json.loads((Path(run_metrics.__file__).resolve().parents[1] / "plugin.json").read_text())
        self.assertEqual(record["harness"]["version"], manifest["version"])
        self.assertEqual(record["harness"]["native_run_ids"], ["native-1"])
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

        updated = self.update(path, 0, {
            "/ticket/preparation_started_at": "2026-09-16T00:40:00Z",
            "/ticket/preflight_passed_at": "2026-09-16T00:50:00Z",
            "/timing/ticket_submitted_at": "2026-09-16T00:30:00Z",
            "/timing/wait_coverage": "complete",
            "/timing/wait_intervals": [
                {"start": "2026-09-16T01:05:00Z", "end": "2026-09-16T01:15:00Z",
                 "reason": "reviewers", "evidence_ref": "review-1"},
                {"start": "2026-09-16T01:10:00Z", "end": "2026-09-16T01:20:00Z",
                 "reason": "ci", "evidence_ref": "ci-1"},
            ],
            "/outcome/plan_approvals_before_mr": 1,
            "/outcome/extra_human_help_before_mr": 0,
            "/outcome/human_event_coverage": "complete",
            "/human_events": [{
                "id": "approval-1", "at": "2026-09-16T01:25:00Z",
                "phase": "before_mr", "actor": "engineer", "action": "plan_approval",
                "active_minutes": None, "evidence_ref": "plan-approval-1",
            }],
            "/mr/url": "https://gitlab.example/mr/1",
            "/mr/initial_sha": "abc123",
            "/mr/created_at": "2026-09-16T01:30:00Z",
            "/run/status": "mr_created",
            "/resources/generation/input_tokens": 100,
            "/resources/generation/cached_input_tokens": 40,
            "/resources/generation/output_tokens": 20,
            "/resources/generation/tool_calls": 7,
            "/resources/generation/model_turns": 3,
            "/resources/generation/cost": 1.25,
            "/resources/generation/currency": "USD",
            "/resources/generation/cost_basis": "billed",
            "/resources/generation/cost_source": "native billing export",
        }, now="2026-09-16T01:31:00Z")

        self.assertEqual(updated["outcome"]["classification"], "L3")
        self.assertEqual(updated["ticket"]["preparation_elapsed_minutes"], 10)
        self.assertEqual(updated["timing"]["time_to_mr_minutes"], 60)
        self.assertEqual(updated["timing"]["waiting_minutes"], 15)
        self.assertEqual(updated["timing"]["execution_minutes"], 15)
        self.assertIn("assistance L3", run_metrics.render_card(updated, path))

    def test_failed_no_mr_preserves_resources_and_keeps_mr_null(self):
        path = self.start()
        record = self.update(path, 0, {
            "/run/status": "failed",
            "/run/stopped_at": "2026-09-16T01:08:00Z",
            "/resources/generation/tool_calls": 2,
            "/resources/generation/model_turns": 1,
            "/missing_reasons/resources/generation/input_tokens": "native usage unavailable",
        })
        self.assertEqual(record["outcome"]["classification"], "no_mr")
        self.assertEqual(record["resources"]["generation"]["tool_calls"], 2)
        self.assertEqual(record["mr"], {"url": None, "initial_sha": None, "created_at": None})
        self.assertIn("failed before an implementation MR", record["outcome"]["reason"])

    def test_resume_updates_same_record_and_restart_links_distinct_record(self):
        path = self.start()
        run_id = run_metrics.load_record(path)["run_id"]
        interrupted = self.update(path, 0, {
            "/run/status": "interrupted",
            "/run/stopped_at": "2026-09-16T01:04:00Z",
        })
        resumed = self.update(path, 1, {
            "/run/status": "running",
            "/run/stopped_at": None,
            "/harness/native_run_ids": ["native-1", "native-2"],
        })
        self.assertEqual(interrupted["run_id"], run_id)
        self.assertEqual(resumed["run_id"], run_id)

        restarted_path = self.start(work_item="RGPAYM-42")
        restarted = self.update(restarted_path, 0, {"/restarted_after_run_id": run_id})
        self.assertNotEqual(restarted["run_id"], run_id)
        self.assertEqual(restarted["restarted_after_run_id"], run_id)

    def test_concurrent_updates_reject_one_stale_writer_without_lost_update(self):
        path = self.start()
        barrier = threading.Barrier(2)
        results = []

        def writer(pointer, value):
            barrier.wait()
            try:
                results.append(self.update(path, 0, {pointer: value}))
            except (run_metrics.RevisionConflict, run_metrics.MetricsBusy) as exc:
                results.append(exc)

        threads = [
            threading.Thread(target=writer, args=("/plan_revisions/human_requested", 1)),
            threading.Thread(target=writer, args=("/plan_revisions/autonomous", 2)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sum(isinstance(item, dict) for item in results), 1)
        self.assertEqual(sum(isinstance(item, (run_metrics.RevisionConflict,
                                                run_metrics.MetricsBusy)) for item in results), 1)
        self.assertEqual(run_metrics.load_record(path)["measurement_notes"]["l3"]["revision"], 1)

    def test_lock_contention_is_nonblocking_and_lock_symlinks_are_rejected(self):
        path = self.start()
        lock_path = run_metrics._lock_path(path)
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(run_metrics.MetricsBusy):
                self.update(path, 0, {"/plan_revisions/autonomous": 1})
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

        lock_path.unlink()
        victim = Path(self.temp_dir.name) / "victim"
        victim.write_text("do not touch")
        lock_path.symlink_to(victim)
        with self.assertRaises(OSError):
            self.update(path, 0, {"/plan_revisions/autonomous": 1})
        self.assertEqual(victim.read_text(), "do not touch")

    def test_record_swap_during_update_cannot_redirect_write(self):
        first_path = self.start(work_item="RGPAYM-A")
        second_path = self.start(work_item="RGPAYM-B")
        original_read = run_metrics._read_record_at
        swapped = False

        def swap_after_read(parent_fd, name):
            nonlocal swapped
            result = original_read(parent_fd, name)
            if not swapped and name == first_path.name:
                first_path.unlink()
                first_path.symlink_to(second_path)
                swapped = True
            return result

        with patch.object(run_metrics, "_read_record_at", side_effect=swap_after_read):
            with self.assertRaises(run_metrics.MetricsBusy):
                self.update(first_path, 0, {"/plan_revisions/autonomous": 1})
        self.assertEqual(run_metrics.load_record(second_path)["measurement_notes"]["l3"]["revision"], 0)

    def test_impossible_values_are_rejected(self):
        cases = [
            {"/resources/generation/input_tokens": True},
            {"/resources/generation/cost": float("inf")},
            {"/resources/generation/tool_calls": -1},
            {"/human_effort/before_mr_or_stop_active_minutes": -0.1},
            {"/outcome/plan_approvals_before_mr": 1.5},
            {"/resources/generation/input_tokens": 2,
             "/resources/generation/cached_input_tokens": 3},
            {"/resources/generation/cost": 1, "/resources/generation/currency": None},
        ]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                path = self.start(work_item=str(uuid.uuid4()))
                self.update(path, 0, values)

    def test_initial_mr_ci_and_review_are_immutable_once_observed(self):
        path = self.start()
        first = self.update(path, 0, {
            "/mr/url": "https://gitlab.example/mr/1",
            "/mr/initial_sha": "first",
            "/mr/created_at": "2026-09-16T01:04:00Z",
            "/review/initial_ci": {"result": "pending", "sha": "first", "evidence_ref": "ci"},
            "/review/initial_review": {"result": "not_yet_reviewed", "sha": "first",
                                         "evidence_ref": "review"},
        })
        observed = self.update(path, 1, {
            "/review/initial_ci": {"result": "passed", "sha": "first", "evidence_ref": "ci"},
            "/review/initial_review": {"result": "accepted_without_changes", "sha": "first",
                                         "evidence_ref": "review"},
        })
        self.assertEqual(observed["review"]["initial_ci"]["result"], "passed")
        for values in (
            {"/mr/initial_sha": "later"},
            {"/mr/url": "https://gitlab.example/mr/2"},
            {"/mr/created_at": "2026-09-16T01:06:00Z"},
            {"/review/initial_ci": {"result": "code_failure", "sha": "first",
                                     "evidence_ref": "ci-2"}},
            {"/review/initial_review": {"result": "changes_requested", "sha": "first",
                                         "evidence_ref": "review-2"}},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.update(path, 2, values)
        self.assertEqual(run_metrics.load_record(path), observed)
        self.assertEqual(first["mr"]["initial_sha"], "first")

    def test_specify_and_review_without_mr_are_not_no_mr_failures(self):
        for mode in ("specify", "review"):
            with self.subTest(mode=mode):
                path = self.start(mode=mode, source_kind="markdown", work_item="requirements.md")
                record = self.update(path, 0, {
                    "/run/status": "failed",
                    "/run/stopped_at": "2026-09-16T01:05:00Z",
                })
                self.assertIsNone(record["outcome"]["classification"])
                self.assertIn("excluded from implementation-MR classification", record["outcome"]["reason"])
                card = run_metrics.render_card(record, path)
                self.assertTrue(card.startswith("running ({} mode)".format(mode)))
                self.assertNotIn("(run failed)", card)

    def test_no_jira_source_is_explicitly_unknown_not_invented(self):
        path = self.start(source_kind="chat", work_item="chat-request-1")
        record = run_metrics.load_record(path)
        self.assertIsNone(record["ticket"]["id"])
        self.assertEqual(record["measurement_notes"]["l3"]["source_work_item"], "chat-request-1")
        self.assertEqual(record["missing_reasons"]["/ticket/id"], "source kind chat has no Jira ticket")

    def test_work_item_is_optional_and_checkpoint_metadata_is_mutable(self):
        path = run_metrics.start_record(
            mode="run",
            repository=Path("/tmp/example-repository"),
            work_item=None,
            source_kind="chat",
            output_dir=self.output_dir,
            now="2026-09-16T01:00:00Z",
        )
        record = self.update(path, 0, {
            "/measurement_notes/l3/workflow_status": "needs-input",
            "/measurement_notes/l3/next_action": "Resolve retention period",
        })
        self.assertIsNone(record["measurement_notes"]["l3"]["source_work_item"])
        self.assertEqual(record["measurement_notes"]["l3"]["workflow_status"], "needs-input")
        self.assertEqual(record["measurement_notes"]["l3"]["next_action"],
                         "Resolve retention period")
        self.assertNotIn("/measurement_notes/l3/next_action", record["missing_reasons"])
        card = run_metrics.render_card(record, path)
        self.assertTrue(card.startswith("needs-input (run running)"))

        reverted = self.update(path, 1, {
            "/measurement_notes/l3/next_action": None,
            "/harness/models": [],
            "/harness/native_run_ids": [],
        })
        self.assertIn("/measurement_notes/l3/next_action", reverted["missing_reasons"])
        self.assertIn("/harness/models", reverted["missing_reasons"])
        self.assertIn("/harness/native_run_ids", reverted["missing_reasons"])

    def test_output_directory_must_resolve_outside_repository(self):
        repository = Path(self.temp_dir.name) / "repository"
        repository.mkdir()
        alias = Path(self.temp_dir.name) / "alias"
        alias.symlink_to(repository, target_is_directory=True)
        for output_dir in (repository / ".metrics", alias / ".metrics"):
            with self.subTest(output_dir=output_dir), self.assertRaises(ValueError):
                run_metrics.start_record(
                    mode="run", repository=repository, source_kind="chat",
                    output_dir=output_dir, now="2026-09-16T01:00:00Z",
                )

    def test_derived_and_identity_fields_cannot_be_patched(self):
        path = self.start()
        for pointer in (
            "/run_id", "/updated_at", "/harness/version", "/outcome/classification",
            "/outcome/reason", "/timing/execution_minutes",
            "/measurement_notes/l3/revision",
        ):
            with self.subTest(pointer=pointer), self.assertRaises(ValueError):
                self.update(path, 0, {pointer: "forged"})

    def test_validate_rejects_missing_reason_key_shape_and_raw_extra_fields(self):
        path = self.start()
        record = json.loads(path.read_text())
        record["unexpected"] = "raw prompt"
        with self.assertRaises(ValueError):
            run_metrics.validate_record(record)
        del record["unexpected"]
        record["missing_reasons"]["ticket/id"] = "wrong pointer form"
        with self.assertRaises(ValueError):
            run_metrics.validate_record(record)

    def test_validation_rejects_forged_derived_classification(self):
        path = self.start()
        record = run_metrics.load_record(path)
        record["outcome"]["classification"] = "L3"
        record["outcome"]["reason"] = "forged"
        with self.assertRaises(ValueError):
            run_metrics.validate_record(record)

    def test_recorded_harness_version_survives_plugin_upgrade(self):
        path = self.start()
        record = run_metrics.load_record(path)
        recorded_version = record["harness"]["version"]
        with patch.object(run_metrics, "_plugin_version", return_value="99.0.0"):
            self.assertEqual(run_metrics.validate_record(record)["harness"]["version"],
                             recorded_version)

    def test_initial_observations_require_complete_mr_and_matching_sha(self):
        path = self.start()
        with self.assertRaises(ValueError):
            self.update(path, 0, {"/mr/url": "https://gitlab.example/mr/1"})
        with self.assertRaises(ValueError):
            self.update(path, 0, {
                "/run/status": "mr_created",
                "/mr/url": "https://gitlab.example/mr/1",
                "/mr/initial_sha": "first",
                "/mr/created_at": "2026-09-16T01:04:00Z",
                "/review/initial_ci": {
                    "result": "passed", "sha": "later", "evidence_ref": "pipeline-2",
                },
            })

    def test_review_contract_enums_are_enforced(self):
        path = self.start()
        base = {
            "/mr/url": "https://gitlab.example/mr/1",
            "/mr/initial_sha": "first",
            "/mr/created_at": "2026-09-16T01:04:00Z",
        }
        invalid = [
            {"/review/followup_status": "done"},
            {"/review/confirmed_defect_count": 1, "/review/confirmed_defects": [{
                "id": "D1", "severity": "high", "found_stage": "review",
                "summary": "bad", "evidence_ref": "finding-1",
            }]},
            {"/review/confirmed_defect_count": 1, "/review/confirmed_defects": [{
                "id": "D1", "severity": "major", "found_stage": "ci",
                "summary": "bad", "evidence_ref": "finding-1",
            }]},
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.update(path, 0, {**base, **values})

    def test_l3_requires_reconciled_complete_human_event_inventory(self):
        path = self.start()
        mr = {
            "/mr/url": "https://gitlab.example/mr/1",
            "/mr/initial_sha": "first",
            "/mr/created_at": "2026-09-16T01:04:00Z",
            "/outcome/plan_approvals_before_mr": 1,
            "/outcome/extra_human_help_before_mr": 0,
            "/outcome/human_event_coverage": "complete",
        }
        with self.assertRaises(ValueError):
            self.update(path, 0, mr)
        with self.assertRaises(ValueError):
            self.update(path, 0, {**mr, "/human_events": [{
                "id": "approval", "at": "2026-09-16T01:03:00Z", "phase": "plan",
                "actor": "engineer", "action": "plan_approval", "active_minutes": None,
                "evidence_ref": "approval-1",
            }]})

    def test_summary_keeps_generation_and_corrections_separate(self):
        path = self.start()
        record = self.update(path, 0, {
            "/resources/corrections/input_tokens": 12,
            "/resources/corrections/cached_input_tokens": 2,
            "/resources/corrections/output_tokens": 4,
            "/resources/corrections/tool_calls": 1,
            "/resources/corrections/model_turns": 1,
            "/resources/corrections/cost": 1.25,
            "/resources/corrections/currency": "USD",
            "/resources/corrections/cost_basis": "billed",
            "/resources/corrections/cost_source": "native billing export",
        })
        card = run_metrics.render_card(record, path)
        self.assertIn("Generation: input unknown", card)
        self.assertIn("Corrections: input 12 / cached 2 / output 4 · cost 1.25 USD (billed)", card)
        self.assertEqual(len(card.splitlines()), 6)

    def test_unknown_human_event_minutes_have_an_indexed_missing_reason(self):
        path = self.start()
        event = {
            "id": "approval-1", "at": "2026-09-16T01:02:00Z", "phase": "before_mr",
            "actor": "engineer", "action": "plan_approval", "active_minutes": None,
            "evidence_ref": "event-1",
        }
        record = self.update(path, 0, {"/human_events": [event]})
        self.assertIn("/human_events/0/active_minutes", record["missing_reasons"])
        run_metrics.validate_record(record)


if __name__ == "__main__":
    unittest.main()
