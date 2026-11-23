"""Methods/llm_integration/llm_calls.py, without a server: requests.post is replaced."""
import pytest

requests = pytest.importorskip("requests")
pytest.importorskip("dotenv")

from Methods.llm_integration import llm_calls  # noqa: E402
from Methods.llm_integration.llm_calls import LLMClient  # noqa: E402


class FakeResponse:
    def __init__(self, body=None, status_code=200, text=""):
        self._body, self.status_code, self.text = body, status_code, text

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} error", response=self)


@pytest.fixture
def posted(monkeypatch):
    """The arguments of every requests.post call; the server answers {"ok": True}."""
    calls = []

    def post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse({"ok": True})

    monkeypatch.setattr(llm_calls.requests, "post", post)
    return calls


@pytest.fixture
def client_for(monkeypatch):
    monkeypatch.setenv("TEST_MODEL", "test-model")
    monkeypatch.setenv("TEST_API_URL", "https://llm.example/v1/endpoint")
    monkeypatch.setenv("TEST_API_TOKEN", "secret")
    return lambda endpoint: LLMClient("TEST_MODEL", "TEST_API_URL", "TEST_API_TOKEN", endpoint)


def test_the_client_reads_its_settings_from_the_environment(client_for):
    client = client_for("chat/completions")

    assert client.model == "test-model"
    assert client.api_url == "https://llm.example/v1/endpoint"
    assert client.api_token == "secret"


def test_chat_completions_sends_messages(client_for, posted):
    result = client_for("chat/completions").call("Hello!", instructions="Be brief.")

    assert result == {"ok": True}
    assert posted[0]["url"] == "https://llm.example/v1/endpoint"
    assert posted[0]["json"] == {"model": "test-model", "messages": [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Hello!"},
    ]}
    assert posted[0]["headers"]["Authorization"] == "Bearer secret"
    assert posted[0]["timeout"] == 30


def test_chat_completions_without_instructions_has_no_system_message(client_for, posted):
    client_for("chat/completions").call("Hello!")

    assert posted[0]["json"]["messages"] == [{"role": "user", "content": "Hello!"}]


def test_responses_endpoint_sends_input_and_instructions(client_for, posted):
    client_for("responses").call("Hello!", instructions="Be brief.")
    client_for("responses").call("Hello!")

    assert posted[0]["json"] == {"model": "test-model", "input": "Hello!", "instructions": "Be brief."}
    assert posted[1]["json"] == {"model": "test-model", "input": "Hello!"}


def test_an_http_error_becomes_a_runtime_error(client_for, monkeypatch, capsys):
    monkeypatch.setattr(llm_calls.requests, "post",
                        lambda url, **kwargs: FakeResponse(status_code=401, text="bad token"))

    with pytest.raises(RuntimeError, match="API call failed"):
        client_for("chat/completions").call("Hello!")
    assert "401" in capsys.readouterr().out


def test_a_connection_error_becomes_a_runtime_error(client_for, monkeypatch):
    def post(url, **kwargs):
        raise requests.exceptions.ConnectionError("no route to host")

    monkeypatch.setattr(llm_calls.requests, "post", post)

    with pytest.raises(RuntimeError, match="no route to host"):
        client_for("chat/completions").call("Hello!")


def test_call_batch_calls_once_per_prompt_in_order(client_for, posted):
    results = client_for("chat/completions").call_batch(["one", "two", "three"])

    assert results == [{"ok": True}] * 3
    assert [call["json"]["messages"][0]["content"] for call in posted] == ["one", "two", "three"]
