import copy
import hashlib
import unittest
from unittest.mock import Mock, patch

from odip_worker.contract import KIT, canonical_bytes, load_json
from odip_worker.energy.profile import (
    calendar_year_hours,
    reference_outputs,
    validate_profile,
)
from odip_worker.publication import validate_job


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.folder = KIT / "fixtures/energy-reference-wasserburg-am-inn-2024"
        self.manifest = load_json(self.folder / "manifest.json")
        self.artifacts = {
            a["artifactId"]: load_json(
                self.folder / "artifacts" / (a["artifactId"] + ".json")
            )
            for a in self.manifest["artifacts"]
        }

    def test_pinned_profile_and_source_mapping_match_exact_bytes(self):
        validate_profile(self.manifest, self.artifacts)
        source = load_json(self.folder / "source/pvgis-era5-wasserburg-2023.json")
        for name, document in reference_outputs(source).items():
            self.assertEqual(
                canonical_bytes(document),
                (self.folder / "artifacts" / (name + ".json")).read_bytes(),
            )
        self.assertEqual(len(self.artifacts["pv-yield"]["values"]), 8784)

    def test_missing_hour_duplicate_hour_wrong_unit_and_invalid_component_fail(self):
        for mutate in [
            lambda a: a["pv-yield"]["values"].pop(),
            lambda a: a["pv-yield"]["values"][1].update(
                start=a["pv-yield"]["values"][0]["start"]
            ),
            lambda a: a["import-tariff"].update(unit="USD/kWh"),
            lambda a: a["component-catalog"]["components"][0].pop("ratedPowerKWp"),
        ]:
            artifacts = copy.deepcopy(self.artifacts)
            mutate(artifacts)
            manifest = copy.deepcopy(self.manifest)
            for descriptor in manifest["artifacts"]:
                descriptor["sha256"] = hashlib.sha256(
                    canonical_bytes(artifacts[descriptor["artifactId"]])
                ).hexdigest()
            with self.assertRaises(Exception):
                validate_profile(manifest, artifacts)

    def test_complete_calendar_year_counts_include_gregorian_leap_rules(self):
        for year, count in [(1900, 8760), (2000, 8784), (2023, 8760), (2024, 8784), (2100, 8760)]:
            with self.subTest(year=year):
                self.assertEqual(calendar_year_hours({
                    "start": f"{year}-01-01T00:00:00Z",
                    "endExclusive": f"{year + 1}-01-01T00:00:00Z",
                    "step": "PT1H",
                }), count)

    def test_partial_rolling_shifted_and_multi_year_publications_fail(self):
        for start, end in [
            ("2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"),
            ("2024-01-01T00:00:00Z", "2024-12-31T00:00:00Z"),
            ("2024-01-01T01:00:00Z", "2025-01-01T01:00:00Z"),
            ("2023-02-01T00:00:00Z", "2024-02-01T00:00:00Z"),
            ("2024-01-01T00:00:00+01:00", "2025-01-01T00:00:00+01:00"),
            ("2024-01-01T00:00:00.000001Z", "2025-01-01T00:00:00.000001Z"),
            ("2024-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            ("2025-01-01T00:00:00Z", "2024-01-01T00:00:00Z"),
        ]:
            with self.subTest(start=start, end=end):
                manifest = copy.deepcopy(self.manifest)
                manifest["metadata"]["period"].update(start=start, endExclusive=end)
                with self.assertRaisesRegex(ValueError, "one complete UTC calendar year"):
                    validate_profile(manifest, self.artifacts)

    def test_modified_artifact_produces_failed_report(self):
        job = {
            "id": "draft",
            "manifest": self.manifest,
            "manifestSha256": hashlib.sha256(
                canonical_bytes(self.manifest)
            ).hexdigest(),
            "claimToken": "claim",
        }
        source = Mock()
        source.iter_content.return_value = [b"{}"]
        finished = Mock()
        finished.json.return_value = {"status": "FAILED"}
        with (
            patch("odip_worker.publication.call", side_effect=[source, finished]) as call,
            self.assertLogs("odip_worker.publication", level="INFO") as logs,
        ):
            self.assertEqual(validate_job("https://odip.test", job)["status"], "FAILED")
        self.assertEqual(
            call.call_args.kwargs["json"]["failureCode"], "profile_validation_failed"
        )
        self.assertEqual(
            set(call.call_args.kwargs["json"]["checks"].values()), {"FAIL"}
        )
        self.assertEqual(logs.records[-1].event, "publication.validation.failed")
        self.assertEqual(logs.records[-1].levelname, "WARNING")
        self.assertEqual(logs.records[-1].publication_id, "draft")
        self.assertGreaterEqual(logs.records[-1].duration_ms, 0)
        self.assertNotIn("claim", " ".join(logs.output))
