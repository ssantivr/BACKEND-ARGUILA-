from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app import ai, mailer
from app.errors import AIUnavailableError


class FakeSmtp:
    instances = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.calls = []
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *details):
        return False

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, message):
        self.calls.append(("send", message["From"], message["To"], message["Subject"], message.get_content()))


@pytest.fixture
def smtp(monkeypatch):
    FakeSmtp.instances = []
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSmtp)
    return FakeSmtp


def test_console_mailer_is_used_when_smtp_is_not_configured(monkeypatch, capsys):
    monkeypatch.delenv("SMTP_HOST", raising=False)

    chosen = mailer.get_mailer()
    chosen.send("ana@example.com", "Hola", "cuerpo del mensaje")

    assert isinstance(chosen, mailer.ConsoleMailer)
    output = capsys.readouterr().out
    assert "ana@example.com" in output and "cuerpo del mensaje" in output


def test_smtp_mailer_translates_send_into_smtp_calls(monkeypatch, smtp):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USER", "mailer")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM", "arquila@example.com")

    chosen = mailer.get_mailer()
    chosen.send("ana@example.com", "Hola", "cuerpo")

    assert isinstance(chosen, mailer.SmtpMailer)
    [server] = smtp.instances
    assert (server.host, server.port) == ("smtp.example.com", 2525)
    assert server.calls == [
        "starttls",
        ("login", "mailer", "secret"),
        ("send", "arquila@example.com", "ana@example.com", "Hola", "cuerpo\n"),
    ]


def test_smtp_mailer_skips_login_without_a_user(monkeypatch, smtp):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.delenv("SMTP_USER", raising=False)

    mailer.get_mailer().send("ana@example.com", "Hola", "cuerpo")

    assert [call for call in smtp.instances[0].calls if call[0] == "login"] == []


class FakeMessages:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def create(self, **request):
        self.requests.append(request)

        if isinstance(self.result, Exception):
            raise self.result

        return self.result


def claude_assistant(result):
    assistant = ai.ClaudeAssistant.__new__(ai.ClaudeAssistant)
    messages = FakeMessages(result)
    assistant._client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return assistant, messages


def response(stop_reason, *blocks):
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks))


def text(value):
    return SimpleNamespace(type="text", text=value)


def test_claude_assistant_returns_only_the_text_blocks():
    assistant, messages = claude_assistant(
        response("end_turn", SimpleNamespace(type="thinking", thinking=""), text("Hola. "), text("Listo."))
    )

    reply = assistant.reply("system prompt", [{"role": "user", "content": "hola"}])

    assert reply == "Hola. Listo."
    [request] = messages.requests
    assert request["model"] == ai.MODEL
    assert request["system"] == "system prompt"
    assert request["messages"] == [{"role": "user", "content": "hola"}]


def test_claude_assistant_handles_refusals_and_empty_answers():
    refused, _ = claude_assistant(response("refusal", text("partial")))
    empty, _ = claude_assistant(response("end_turn"))

    assert refused.reply("s", []) == ai.REFUSAL_REPLY
    assert empty.reply("s", []) == ai.EMPTY_REPLY


def test_claude_assistant_turns_sdk_errors_into_the_application_error():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    failures = [
        anthropic.APIConnectionError(request=request),
        anthropic.RateLimitError("busy", response=httpx.Response(429, request=request), body=None),
        anthropic.AuthenticationError("bad key", response=httpx.Response(401, request=request), body=None),
        anthropic.InternalServerError("down", response=httpx.Response(500, request=request), body=None),
    ]

    for failure in failures:
        assistant, _ = claude_assistant(failure)

        with pytest.raises(AIUnavailableError):
            assistant.reply("s", [])
