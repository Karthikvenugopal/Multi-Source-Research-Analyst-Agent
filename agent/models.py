"""Structured model contracts and a provider-neutral LangChain adapter."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from agent import prompts


class ResearchRequirements(BaseModel):
    """Concise research requirements derived from the user question."""

    requirements: list[str] = Field(default_factory=list, max_length=8)
    subquestions: list[str] = Field(default_factory=list, max_length=8)


class ResearchDecision(BaseModel):
    """One inspect/search-or-finish decision in the top-level loop."""

    action: Literal["search", "finish"]
    bundle: str | None = None
    query: str | None = Field(default=None, max_length=500)
    action_summary: str = Field(default="", max_length=500)
    unresolved_gaps: list[str] = Field(default_factory=list, max_length=8)


class ResearchModel(Protocol):
    """Minimal high-level model contract used by the runtime and test fakes."""

    def analyze(self, question: str) -> ResearchRequirements: ...

    def decide(self, payload: dict[str, Any]) -> ResearchDecision: ...

    def write_report(self, payload: dict[str, Any]) -> str: ...

    def repair_report(self, payload: dict[str, Any]) -> str: ...


class LangChainResearchModel:
    """Adapt any supported LangChain chat model to structured agent operations."""

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    def analyze(self, question: str) -> ResearchRequirements:
        human = f"Question: {question}\n\nReturn the research requirements."
        return self._structured(ResearchRequirements, prompts.REQUIREMENTS_SYSTEM, human)

    def decide(self, payload: dict[str, Any]) -> ResearchDecision:
        human = (
            f"Question: {payload['question']}\n\n"
            f"Requirements: {payload['requirements']}\n"
            f"Available bundles (quoted capability data):\n{payload['bundle_catalog']}\n\n"
            f"Attempted queries: {payload['queries_attempted']}\n"
            f"Current unresolved gaps: {payload['unresolved_gaps']}\n"
            f"Detected conflict summaries: {payload['conflicts']}\n"
            f"Selected evidence passages:\n{payload['evidence_context']}\n\n"
            "Choose the next bounded action."
        )
        return self._structured(ResearchDecision, prompts.DECISION_SYSTEM, human)

    def write_report(self, payload: dict[str, Any]) -> str:
        human = (
            f"Question: {payload['question']}\n"
            f"Research requirements: {payload['requirements']}\n"
            f"Stop reason: {payload['stop_reason']}\n"
            f"Unresolved gaps: {payload['unresolved_gaps']}\n"
            f"Detected conflicts: {payload['conflicts']}\n\n"
            f"Evidence passages:\n{payload['evidence_context']}\n\n"
            "Write the evidence-grounded report."
        )
        return self._text(prompts.REPORT_SYSTEM, human)

    def repair_report(self, payload: dict[str, Any]) -> str:
        human = (
            f"Verifier errors: {payload['verification_errors']}\n\n"
            f"Available evidence passages:\n{payload['evidence_context']}\n\n"
            f"Draft report:\n{payload['draft_report']}\n\n"
            "Return only the repaired report body."
        )
        return self._text(prompts.REPAIR_SYSTEM, human)

    def _structured(self, schema: type[BaseModel], system: str, human: str):
        structured = self.llm.with_structured_output(schema)
        result = structured.invoke([("system", system), ("human", human)])
        return result if isinstance(result, schema) else schema.model_validate(result)

    def _text(self, system: str, human: str) -> str:
        response = self.llm.invoke([("system", system), ("human", human)])
        if hasattr(response, "content"):
            return str(response.content)
        return response if isinstance(response, str) else str(response)
