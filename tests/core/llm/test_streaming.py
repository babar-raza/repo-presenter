"""Opt-in streaming transport accumulates into the same reply shape as a non-streaming call."""

from types import SimpleNamespace as NS

from repo_presenter.core.llm import jobs


class _Completions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if not kwargs.get("stream"):
            raise AssertionError("non-streaming call made while streaming is enabled")
        usage = NS(prompt_tokens=3, completion_tokens=2, total_tokens=5)
        return iter(
            [
                NS(id="r1", model="m", usage=None,
                   choices=[NS(delta=NS(content="he"), finish_reason=None)]),
                NS(id="r1", model="m", usage=None,
                   choices=[NS(delta=NS(content="llo"), finish_reason="stop")]),
                NS(id="r1", model="m", usage=usage, choices=[]),
            ]
        )


def test_streaming_accumulates_content_usage_and_finish(monkeypatch):
    comps = _Completions()
    client = NS(chat=NS(completions=comps))
    monkeypatch.setattr(jobs.transport, "build_client", lambda config: client)
    monkeypatch.setenv(jobs.STREAMING_VARIABLE, "1")
    reply = jobs._complete(None, {"model": "m", "messages": []})
    assert (reply.content, reply.model, reply.request_id) == ("hello", "m", "r1")
    assert (reply.prompt_tokens, reply.completion_tokens, reply.total_tokens) == (3, 2, 5)
    assert reply.finish_reason == "stop"
    assert comps.kwargs["stream"] is True


def test_default_remains_non_streaming(monkeypatch):
    seen = {}

    class C:
        def create(self, **kw):
            seen.update(kw)
            return NS(usage=None, model="m", id="x",
                      choices=[NS(message=NS(content="ok"), finish_reason="stop")])

    monkeypatch.setattr(jobs.transport, "build_client", lambda c: NS(chat=NS(completions=C())))
    monkeypatch.delenv(jobs.STREAMING_VARIABLE, raising=False)
    assert jobs._complete(None, {"model": "m"}).content == "ok"
    assert "stream" not in seen
