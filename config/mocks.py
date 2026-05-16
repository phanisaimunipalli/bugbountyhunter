MOCK_SCRAPER_RESULT = [
    {
        "repo_url": "https://github.com/psf/requests",
        "issue_url": "https://github.com/psf/requests/issues/6821",
        "issue_title": "JSONDecodeError not properly caught in response.json()",
        "issue_body": (
            "When the server returns a 200 with invalid JSON, calling response.json() "
            "raises json.JSONDecodeError instead of requests.JSONDecodeError. "
            "Reproducible with: r = requests.get(url); r.json() where body is 'not-json'."
        ),
        "issue_number": 6821,
        "fixability_score": 0.92,
    }
]

MOCK_ANALYST_RESULT = {
    "root_cause": (
        "In requests/models.py, Response.json() calls json.loads() directly without "
        "catching json.JSONDecodeError and re-raising as requests.exceptions.JSONDecodeError."
    ),
    "affected_files": ["requests/models.py"],
    "fix_approach": (
        "Wrap the json.loads() call in a try/except json.JSONDecodeError block "
        "and raise requests.exceptions.JSONDecodeError with the original exception chained."
    ),
    "confidence_score": 0.91,
}

MOCK_PATCH_RESULT = {
    "patch_diff": """\
--- a/requests/models.py
+++ b/requests/models.py
@@ -897,7 +897,10 @@ class Response:
         if not self.encoding and self.content and len(self.content) > 3:
             encoding = guess_json_utf(self.content)
             if encoding is not None:
-                return complexjson.loads(self.content.decode(encoding), **kwargs)
+                try:
+                    return complexjson.loads(self.content.decode(encoding), **kwargs)
+                except JSONDecodeError as e:
+                    raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)
         try:
             return complexjson.loads(self.text, **kwargs)
         except JSONDecodeError as e:
""",
    "test_code": """\
def test_json_decode_error_is_requests_exception():
    import requests
    from requests.exceptions import JSONDecodeError
    r = requests.models.Response()
    r._content = b"not-valid-json"
    r.encoding = "utf-8"
    with pytest.raises(JSONDecodeError):
        r.json()
""",
    "explanation": (
        "Wrapped json.loads with a try/except to re-raise as requests.exceptions.JSONDecodeError."
    ),
}

MOCK_VERIFIER_RESULT = {
    "passed": True,
    "test_output": "47 passed, 0 failed in 8.32s",
    "retry_count": 0,
}

MOCK_PR_RESULT = {
    "pr_url": "https://github.com/psf/requests/pull/6834",
    "comment_posted": True,
}

MOCK_EVERMIND_MEMORY: dict = {}
