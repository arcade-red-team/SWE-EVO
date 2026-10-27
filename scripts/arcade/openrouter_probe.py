#!/usr/bin/env python3
"""Check a fixed free OpenRouter endpoint and an optional synthetic tool call.

This is not a benchmark runner. It sends no repository content and never writes
the API key or response body. The requested price and provider constraints
must also be enforced in the eventual agent runner.
"""

import argparse
from decimal import Decimal, InvalidOperation
import json
import os
import sys
import urllib.error
import urllib.request


MODEL = "cohere/north-mini-code:free"
PROVIDER = "cohere"
BASE_URL = "https://openrouter.ai/api/v1"


def check_catalog(data):
    if not isinstance(data, dict) or data.get("id") != MODEL:
        raise ValueError("unexpected model metadata")
    endpoints = data.get("endpoints")
    if not isinstance(endpoints, list):
        raise ValueError("missing endpoints")
    choices = [item for item in endpoints if isinstance(item, dict) and item.get("tag") == PROVIDER]
    if len(choices) != 1:
        raise ValueError("expected one matching provider endpoint")
    endpoint = choices[0]
    price = endpoint.get("pricing")
    if not isinstance(price, dict):
        raise ValueError("missing pricing")
    try:
        if any(Decimal(str(price[name])) != 0 for name in ("prompt", "completion")):
            raise ValueError("endpoint is not zero-priced")
    except (KeyError, InvalidOperation):
        raise ValueError("invalid endpoint price") from None
    parameters = endpoint.get("supported_parameters")
    if not isinstance(parameters, list) or not {"tools", "tool_choice"}.issubset(parameters):
        raise ValueError("endpoint lacks required tool parameters")
    return {"model": MODEL, "provider": PROVIDER, "prompt_price": "0", "completion_price": "0",
            "context_length": endpoint.get("context_length")}


def smoke_payload():
    return {
        "model": MODEL,
        "input": [{"role": "user", "content": "Call the echo_number tool with value 7."}],
        "store": False,
        "max_output_tokens": 200,
        "tools": [{"type": "function", "name": "echo_number", "description": "Accept a number",
                   "parameters": {"type": "object", "properties": {"value": {"type": "integer"}},
                                  "required": ["value"], "additionalProperties": False}, "strict": True}],
        "tool_choice": {"type": "function", "name": "echo_number"},
        "provider": {"only": [PROVIDER], "allow_fallbacks": False, "require_parameters": True,
                     "max_price": {"prompt": 0, "completion": 0, "request": 0}},
    }


def check_response(data):
    if not isinstance(data, dict) or data.get("model") != MODEL or data.get("status") != "completed":
        raise ValueError("unexpected model or incomplete response")
    usage = data.get("usage")
    if not isinstance(usage, dict) or type(usage.get("cost")) not in (int, float) or usage["cost"] != 0:
        raise ValueError("response cost is absent or nonzero")
    calls = [item for item in data.get("output", []) if isinstance(item, dict)
             and item.get("type") == "function_call" and item.get("name") == "echo_number"]
    if len(calls) != 1:
        raise ValueError("expected one echo_number call")
    try:
        arguments = json.loads(calls[0].get("arguments", ""))
    except (TypeError, json.JSONDecodeError):
        raise ValueError("invalid tool arguments") from None
    if arguments != {"value": 7} or type(arguments.get("value")) is not int:
        raise ValueError("unexpected tool arguments")
    return {"model": MODEL, "status": "completed", "tool_call_correct": True,
            "cost": usage["cost"], "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens")}


def request_json(request):
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="send one synthetic free-model tool request")
    args = parser.parse_args(argv)
    try:
        catalog = request_json(urllib.request.Request(f"{BASE_URL}/models/{MODEL}/endpoints"))
        result = {"catalog": check_catalog(catalog.get("data"))}
        if args.smoke:
            key = os.environ.get("OPENROUTER_API_KEY")
            if not key:
                raise ValueError("OPENROUTER_API_KEY is missing")
            request = urllib.request.Request(f"{BASE_URL}/responses", data=json.dumps(smoke_payload()).encode(),
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
            result["synthetic_smoke"] = check_response(request_json(request))
        print(json.dumps(result, sort_keys=True))
    except (OSError, urllib.error.URLError, ValueError, TypeError) as error:
        # Do not print HTTP bodies, request headers, credentials or local paths.
        if isinstance(error, urllib.error.HTTPError):
            print(f"openrouter probe: HTTP {error.code}", file=sys.stderr)
        else:
            print(f"openrouter probe: {type(error).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
