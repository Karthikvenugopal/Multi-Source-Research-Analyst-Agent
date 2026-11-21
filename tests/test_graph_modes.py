"""Mode facade coverage for preserved legacy and default agentic behavior."""

import graph as graph_module


class FakeRunner:
    def __init__(self, label):
        self.label = label

    def run(self, question):
        return {"mode": self.label, "question": question}

    def stream(self, question):
        yield "done", self.run(question)


def test_agentic_mode_delegates_to_injected_runtime():
    graph = graph_module.ResearchGraph(mode="agentic", runtime=FakeRunner("agentic"))
    assert graph.run("q")["mode"] == "agentic"
    assert list(graph.stream("q"))[0][0] == "done"


def test_legacy_mode_remains_available(monkeypatch):
    monkeypatch.setattr(
        graph_module, "LegacyResearchGraph", lambda: FakeRunner("legacy")
    )
    graph = graph_module.ResearchGraph(mode="legacy")
    assert graph.run("q")["mode"] == "legacy"
    assert list(graph.stream("q"))[0][0] == "done"


def test_invalid_mode_is_rejected():
    try:
        graph_module.ResearchGraph(mode="unknown", runtime=FakeRunner("x"))
    except ValueError as exc:
        assert "agentic" in str(exc)
    else:
        raise AssertionError("invalid mode was accepted")
