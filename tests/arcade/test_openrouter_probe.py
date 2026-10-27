"""Controls for the synthetic, zero-priced OpenRouter probe."""

import copy
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/arcade/openrouter_probe.py"
spec = importlib.util.spec_from_file_location("openrouter_probe", SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def catalog():
    return {"id": probe.MODEL, "endpoints": [{"tag": probe.PROVIDER,
        "pricing": {"prompt": "0", "completion": "0"}, "context_length": 256000,
        "supported_parameters": ["tools", "tool_choice"]}]}


def response():
    return {"model": probe.MODEL, "status": "completed", "usage": {"cost": 0},
            "output": [{"type": "function_call", "name": "echo_number", "arguments": '{"value":7}'}]}


class OpenRouterProbeTest(unittest.TestCase):
    def test_catalog_zero_price_provider_and_tool_controls(self):
        self.assertEqual(probe.check_catalog(catalog())["prompt_price"], "0")
        for change in ("price", "provider", "tools", "duplicate"):
            data = copy.deepcopy(catalog())
            endpoint = data["endpoints"][0]
            if change == "price":
                endpoint["pricing"]["completion"] = "0.0001"
            elif change == "provider":
                endpoint["tag"] = "other"
            elif change == "tools":
                endpoint["supported_parameters"] = []
            else:
                data["endpoints"].append(copy.deepcopy(endpoint))
            with self.subTest(change=change), self.assertRaises(ValueError):
                probe.check_catalog(data)

    def test_request_constraints_and_response_fail_closed(self):
        payload = probe.smoke_payload()
        self.assertEqual(payload["model"], probe.MODEL)
        self.assertEqual(payload["provider"]["max_price"], {"prompt": 0, "completion": 0, "request": 0})
        self.assertFalse(payload["provider"]["allow_fallbacks"])
        self.assertTrue(probe.check_response(response())["tool_call_correct"])
        cases = []
        for key, value in (("status", "failed"), ("model", "other"), ("usage", {}),
                           ("usage", {"cost": 0.01}), ("output", [])):
            item = copy.deepcopy(response())
            item[key] = value
            cases.append(item)
        wrong = copy.deepcopy(response())
        wrong["output"][0]["arguments"] = '{"value":true}'
        cases.append(wrong)
        for item in cases:
            with self.subTest(item=item), self.assertRaises(ValueError):
                probe.check_response(item)


if __name__ == "__main__":
    unittest.main()
