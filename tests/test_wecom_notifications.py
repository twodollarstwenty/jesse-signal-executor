def test_build_wecom_text_payload_uses_text_message_shape():
    from apps.notifications.wecom import build_text_payload

    payload = build_text_payload("hello world")

    assert payload == {
        "msgtype": "text",
        "text": {"content": "hello world"},
    }


def test_send_wecom_message_noops_when_webhook_missing(monkeypatch):
    from apps.notifications.wecom import send_text_message

    monkeypatch.delenv("WECOM_BOT_WEBHOOK", raising=False)

    sent = send_text_message("hello")

    assert sent is False


def test_send_wecom_message_works_without_requests_dependency(monkeypatch):
    import json
    import types
    import builtins

    from apps.notifications.wecom import send_text_message

    monkeypatch.setenv("NOTIFY_ENABLED", "1")
    monkeypatch.setenv("WECOM_BOT_WEBHOOK", "https://example.invalid/webhook")

    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"errcode":0,"errmsg":"ok"}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = request.data.decode("utf-8")
        return FakeResponse()

    class FakeRequest:
        def __init__(self, url, data=None, headers=None, method=None):
            self.full_url = url
            self.data = data
            self.headers = headers or {}
            self.method = method

    fake_request_module = types.SimpleNamespace(urlopen=fake_urlopen, Request=FakeRequest)
    fake_urllib = types.SimpleNamespace(request=fake_request_module)
    monkeypatch.setattr("apps.notifications.wecom.urllib", fake_urllib)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ModuleNotFoundError("No module named 'requests'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert send_text_message("hello") is True
    assert captured["url"] == "https://example.invalid/webhook"
    assert captured["timeout"] == 5
    assert json.loads(captured["body"]) == {
        "msgtype": "text",
        "text": {"content": "hello"},
    }
