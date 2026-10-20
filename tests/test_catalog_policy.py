"""Regression coverage for the public provenance boundary."""
import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("catalog_policy", ROOT / "tools/validate_catalog.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.entries = policy.load_json(ROOT / "catalog/manifest.json")["entries"]
        self.promoted = copy.deepcopy(next(e for e in self.entries if e["id"] == "principal-agile-coach"))

    def test_original_and_promoted_sources_pass(self):
        for entry in self.entries:
            with self.subTest(role=entry["id"]):
                policy.validate_asset(entry)

    def test_private_source_is_rejected(self):
        self.promoted["sourceVisibility"] = "private"
        with self.assertRaisesRegex(policy.CatalogError, "fonte"):
            policy.validate_asset(self.promoted)

    def test_enterprise_repository_is_rejected(self):
        self.promoted["sourceRepository"] = "HUBTECH-DEV/hubicg-enterprise"
        with self.assertRaisesRegex(policy.CatalogError, "origem"):
            policy.validate_asset(self.promoted)

    def test_unapproved_revision_is_rejected(self):
        self.promoted["sourceCommitSha"] = "0" * 40
        with self.assertRaisesRegex(policy.CatalogError, "sourceCommitSha"):
            policy.validate_asset(self.promoted)

    def test_transformed_blob_is_rejected(self):
        self.promoted["sourceBlobSha"] = "0" * 40
        with self.assertRaisesRegex(policy.CatalogError, "Git blob"):
            policy.validate_asset(self.promoted)

    def test_noncanonical_source_path_is_rejected(self):
        self.promoted["sourcePath"] = "other/principal-agile-coach.json"
        with self.assertRaisesRegex(policy.CatalogError, "sourcePath"):
            policy.validate_asset(self.promoted)


if __name__ == "__main__":
    unittest.main()
