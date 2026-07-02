"""LLM-as-judge evaluation for research reports.

The agent's `tools.py` assigns each source a fixed confidence constant
(web=0.8, wikipedia=0.9, arxiv=0.85). Those numbers describe *where* a finding
came from, not *how good the report is*. This module grades the actual output
with a separate model (Gemini, temperature 0) against the retrieved evidence:

- faithfulness:       are the report's claims supported by the retrieved evidence,
                      rather than invented? (the inverse of hallucination)
- answer_relevance:   does the report actually answer the question that was asked?
- citation_coverage:  are substantive claims attributed to sources?

Scores are in [0, 1]. Using a model to grade output against retrieved context is
the same idea behind RAG eval frameworks (RAGAS, etc.), implemented directly so
there is no hidden magic.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config import Config


class JudgeVerdict(BaseModel):
    """Structured grade returned by the judge model."""

    faithfulness: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of the report's factual claims that are supported "
                    "by the retrieved evidence. 1.0 = every claim is grounded.",
    )
    answer_relevance: float = Field(
        ge=0.0, le=1.0,
        description="How directly and completely the report answers the question.",
    )
    citation_coverage: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of substantive claims attributed to a source.",
    )
    rationale: str = Field(
        description="One short paragraph justifying the three scores.",
    )

    @property
    def overall(self) -> float:
        return round(
            (self.faithfulness + self.answer_relevance + self.citation_coverage) / 3,
            4,
        )


_SYSTEM_PROMPT = """You are a strict, impartial evaluator of research reports.

You are given a QUESTION, the RETRIEVED EVIDENCE that was available to the writer,
and the REPORT the writer produced. Grade ONLY what is in front of you. Do not use
outside knowledge to fill gaps, and do not reward fluent writing that is not
supported by the evidence.

Score three metrics, each from 0.0 to 1.0:

1. faithfulness - Of the factual claims in the report, what fraction is directly
   supported by the retrieved evidence? Penalise claims that are absent from the
   evidence or contradict it. This is the inverse of hallucination.

2. answer_relevance - How directly and completely does the report answer the
   QUESTION? A thorough, on-topic answer scores high; an evasive or off-topic one
   scores low.

3. citation_coverage - Of the substantive claims, what fraction is attributed to a
   source (named source type, title, or URL)? Unattributed assertions lower this.

Be calibrated: reserve scores above 0.9 for genuinely excellent reports and below
0.4 for poor ones. Provide a brief rationale."""


class ReportJudge:
    """Grades a research report against its retrieved evidence using Gemini."""

    def __init__(self, model: Optional[str] = None, evidence_char_limit: int = 1200):
        if not Config.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is required to run the judge. Set it in your .env."
            )
        from langchain_google_genai import ChatGoogleGenerativeAI
        from llm_manager import gemini_rate_limiter

        self.model = model or Config.LLM_MODEL
        self.evidence_char_limit = evidence_char_limit
        llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0,
            max_retries=0,  # rate limiter prevents 429s; retries would waste daily quota
            rate_limiter=gemini_rate_limiter(self.model),
        )
        # Structured output guarantees we get parseable, in-range scores back.
        self._judge = llm.with_structured_output(JudgeVerdict)

    def _format_evidence(self, findings: List[Dict[str, Any]]) -> str:
        if not findings:
            return "(no evidence was retrieved)"
        lines = []
        for i, f in enumerate(findings, 1):
            source = f.get("source", "unknown").upper()
            title = f.get("title", "Untitled")
            content = (f.get("content", "") or "")[: self.evidence_char_limit]
            lines.append(f"[{i}] ({source}) {title}\n{content}")
        return "\n\n".join(lines)

    def evaluate(
        self,
        question: str,
        report: str,
        findings: List[Dict[str, Any]],
    ) -> JudgeVerdict:
        """Return a JudgeVerdict for one (question, report, evidence) triple."""
        evidence = self._format_evidence(findings)
        human = (
            f"QUESTION:\n{question}\n\n"
            f"RETRIEVED EVIDENCE:\n{evidence}\n\n"
            f"REPORT:\n{report}\n\n"
            "Grade the report now."
        )
        try:
            return self._judge.invoke(
                [("system", _SYSTEM_PROMPT), ("human", human)]
            )
        except Exception as exc:  # never let one bad grade kill a whole run
            return JudgeVerdict(
                faithfulness=0.0,
                answer_relevance=0.0,
                citation_coverage=0.0,
                rationale=f"Judge error: {exc}",
            )
