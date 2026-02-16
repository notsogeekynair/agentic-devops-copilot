import json
from handler import health

def test_health_ok():
    resp = health({}, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "ok"
