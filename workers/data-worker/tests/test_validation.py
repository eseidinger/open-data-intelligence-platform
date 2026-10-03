import unittest

from odip_worker.normalization import normalize
from odip_worker.validation import validate_payload


class PayloadValidationTests(unittest.TestCase):
    def test_validates_json_and_fingerprints_its_shape(self) -> None:
        result = validate_payload(b'[{"timestamp":"2026-01-01","value":42}]', "application/json; charset=utf-8")

        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["detectedFormat"], "JSON")
        self.assertEqual(result["recordCount"], 1)
        self.assertRegex(result["schemaFingerprint"], r"^[a-f0-9]{64}$")

    def test_marks_malformed_json_as_invalid_without_discarding_it(self) -> None:
        result = validate_payload(b'{not json}', "application/json")

        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(result["detectedFormat"], "JSON")
        self.assertIn("failureReason", result)

    def test_validates_csv_records_and_columns(self) -> None:
        result = validate_payload(b"timestamp,value\n2026-01-01,42\n2026-01-02,43\n", "text/csv")

        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["detectedFormat"], "CSV")
        self.assertEqual(result["recordCount"], 2)

    def test_marks_unknown_content_as_unsupported(self) -> None:
        result = validate_payload(b"binary", "application/octet-stream")

        self.assertEqual(result, {"status": "UNSUPPORTED", "detectedFormat": "application/octet-stream"})

    def test_normalizes_single_value_eurostat_response(self) -> None:
        payload = b'{"value":{"0":22.474},"dimension":{"geo":{"category":{"index":{"DE":0}}},"time":{"category":{"index":{"2024":0}}},"unit":{"category":{"index":{"PC":0}}}}}'

        self.assertEqual(normalize(payload, "EUROSTAT_RENEWABLE_SHARE"), {"indicatorCode": "RENEWABLE_ENERGY_SHARE", "geoCode": "DE", "observationYear": 2024, "unitCode": "PC", "observationValue": 22.474})
