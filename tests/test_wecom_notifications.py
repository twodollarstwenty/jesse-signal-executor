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
