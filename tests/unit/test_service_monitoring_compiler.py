#!/usr/bin/env python3
"""Offline tests for the application monitoring compilation contract."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("monitoring_compiler", ROOT / "scripts/compile-service-monitoring.py")
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)

SAMPLE = {
    "schema_version": 1, "service": "n8n", "environment": "development",
    "http": [{"url": "https://n8n.luft-alex.de/", "expected_status": 200}],
    "tls": [{"target": "n8n.luft-alex.de:443"}],
    "dns": [{"name": "n8n.luft-alex.de", "type": "A"}],
    "labels": {"component": "service-probe"},
}


class ManifestContractTests(unittest.TestCase):
    def test_compiles_owned_labels_and_targets(self):
        value = compiler.compile_manifest(SAMPLE)
        self.assertEqual(value["files"]["http"][0]["targets"], ["https://n8n.luft-alex.de/"])
        self.assertEqual(value["files"]["http"][0]["labels"]["service"], "n8n")
        self.assertEqual(value["dns_names"], ["n8n.luft-alex.de"])

    def test_rejects_direct_ip_literal(self):
        doc = json.loads(json.dumps(SAMPLE))
        doc["http"][0]["url"] = "https://127.0.0.1/"
        with self.assertRaises(ValueError):
            compiler.compile_manifest(doc)

    def test_rejects_reserved_label_injection(self):
        doc = json.loads(json.dumps(SAMPLE))
        doc["labels"]["job"] = "prometheus"
        with self.assertRaises(ValueError):
            compiler.compile_manifest(doc)

    def test_rejects_invalid_service_path(self):
        doc = json.loads(json.dumps(SAMPLE))
        doc["service"] = "../prometheus"
        with self.assertRaises(ValueError):
            compiler.compile_manifest(doc)

    def test_rejects_http_url_with_credentials(self):
        doc = json.loads(json.dumps(SAMPLE))
        doc["http"][0]["url"] = "https://user:pass@n8n.luft-alex.de/"
        with self.assertRaises(ValueError):
            compiler.compile_manifest(doc)


    def test_rejects_non_list_check_collections(self):
        for kind, invalid in (("http", "string"), ("tls", {"target": "example.org:443"}), ("dns", None)):
            with self.subTest(kind=kind):
                doc = json.loads(json.dumps(SAMPLE))
                doc[kind] = invalid
                with self.assertRaises(ValueError):
                    compiler.compile_manifest(doc)

    def test_rejects_boolean_values_in_numeric_schema(self):
        for field, value in (("schema_version", True), ("expected_status", True)):
            with self.subTest(field=field):
                doc = json.loads(json.dumps(SAMPLE))
                if field == "expected_status":
                    doc["http"][0][field] = value
                else:
                    doc[field] = value
                with self.assertRaises(ValueError):
                    compiler.compile_manifest(doc)

    def test_rejects_ambiguous_http_authority(self):
        for url in ("https://n8n.luft-alex.de.:443/", "https://n8n.luft-alex.de:0443/",
                    "https://n8n.luft-alex.de\\\\@evil.example/",
                    "https://n8n.luft-alex.de:443/#fragment"):
            with self.subTest(url=url):
                doc = json.loads(json.dumps(SAMPLE))
                doc["http"][0]["url"] = url
                with self.assertRaises(ValueError):
                    compiler.compile_manifest(doc)

    def test_atomic_json_write(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp) / "targets.json"
            compiler.write_atomic(target, [{"targets": ["https://n8n.luft-alex.de/"]}])
            self.assertEqual(json.loads(target.read_text())[0]["targets"], ["https://n8n.luft-alex.de/"])


if __name__ == "__main__":
    unittest.main()
