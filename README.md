# Multi-Source Research Analyst Agent

[![CI](https://github.com/Karthikvenugopal/Multi-Source-Research-Analyst-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Karthikvenugopal/Multi-Source-Research-Analyst-Agent/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

![LangGraph](https://img.shields.io/badge/LangGraph-agent-1C3C3C)
![Google Gemini](https://img.shields.io/badge/LLM-Gemini-4285F4)
![Gradio](https://img.shields.io/badge/UI-Gradio-F97316)
![Tavily](https://img.shields.io/badge/search-Tavily-6366F1)
![pytest](https://img.shields.io/badge/tested-pytest-0A9EDC)

An autonomous research agent built with **LangGraph**. Given a question, it decides
which sources to consult (web, Wikipedia, academic papers), gathers evidence across
them, and synthesizes a single cited report — and its output quality is measured by
a model-graded evaluation harness rather than asserted.

## Highlights

- **Plan-execute control flow** — a planner (LLM) chooses which sources to use and
  a tailored query for each in one structured-output call; retrieval then runs in
  **parallel**, followed by synthesis and report generation. ~3 LLM calls per
  question, with a deterministic fallback so it never stalls.
- **Multi-source retrieval** — web search (Tavily), Wikipedia, and ArXiv, each
  normalized into a common finding schema with source attribution.
- **Measured, not asserted** — an LLM-as-judge scores every report on faithfulness,
  answer relevance, and citation coverage (see [Evaluation](#evaluation)).
- **Tested and CI-gated** — 29 hermetic unit tests (no network or API keys) run on
  every push via GitHub Actions.
- **Pluggable LLMs** — Google Gemini (default, free tier), OpenAI, or local
  HuggingFace models, selected by environment variable.

## Evaluation

Report quality is measured by an **LLM-as-judge** (`evals/judge.py`): a separate
Gemini model grades each generated report against the evidence the agent actually
retrieved, on three axes in `[0, 1]`.

- **Faithfulness** — are the report's claims grounded in the retrieved evidence (not hallucinated)?
- **Answer relevance** — does the report actually answer the question?
- **Citation coverage** — are substantive claims attributed to a source?

Reproduce with `python -m evals.run_eval` (questions in `datasets/eval_questions.jsonl`).

_Agent: `gemini-2.5-flash-lite` · Judge: `gemini-2.5-flash` (temperature 0) · 3 questions (v1 iterative agent)._
_(Eval runs the agent on the cheaper flash-lite to stay within free-tier limits; the default agent model is `gemini-2.5-flash`.)_

| Question | Faithfulness | Relevance | Citations | Overall |
| --- | :---: | :---: | :---: | :---: |
| Factual — *what is RAG?* | 1.00 | 0.95 | 0.90 | **0.95** |
| Technical — *transformers & self-attention* | 0.30 | 0.10 | 0.50 | **0.30** |
| Comparative — *solar vs. wind energy* | 1.00 | 0.90 | 1.00 | **0.97** |
| **Mean** | **0.77** | **0.65** | **0.80** | **0.74** |

**What the eval surfaced:** the technical question (q2) scored poorly because the
v1 agent sent the *full natural-language question* as the search query to every
source; for long questions this returned weak Wikipedia/ArXiv hits, so the report
couldn't ground its answer. That finding drove the **plan-execute redesign**
(below): a planner emits a concise, source-tailored query per source and fetches
them in parallel. The redesigned agent is **~4× faster** (q1: 13s vs ~60s) and
retrieves more broadly (q2 now pulls all three sources, including web); on re-run
it scores **0.95** on q1.

> **Note on eval scope.** A full re-score of the redesigned agent is bounded by
> the Gemini free tier (~20 requests/day per model), which this project stays
> within by design (it even rate-limits itself — see `gemini_rate_limiter`). The
> harness scales to the whole set on a key with higher limits.

## Architecture

```
   ┌───────────┐   1 LLM call: choose sources + a tailored query for each
   │  Planner  │
   └─────┬─────┘
         │ research plan
         ▼
   ┌───────────┐         ┌──────────────┐
   │  Gather   │ ──────▶ │ Web (Tavily) │
   │ (parallel │ ──────▶ │ Wikipedia    │ ──▶ findings
   │  fetch)   │ ──────▶ │ ArXiv        │
   └─────┬─────┘         └──────────────┘
         ▼
   ┌────────────┐      ┌──────────┐
   │ Synthesize │ ───▶ │  Report  │ ──▶ cited report
   └────────────┘      └──────────┘
```

| Module | Responsibility |
| --- | --- |
| `graph.py` | LangGraph pipeline: planner → gather → synthesize → report |
| `nodes.py` | Planner (sources + queries), parallel gather, synthesis, report |
| `tools.py` | Tavily / Wikipedia / ArXiv retrieval → common finding schema |
| `llm_manager.py` | Provider selection (Gemini / OpenAI / HuggingFace) |
| `state.py` | Typed `AgentState` |
| `evals/` | Model-graded evaluation (judge + runner + dataset) |
| `app.py` | Gradio web UI |

## Quickstart

```bash
git clone https://github.com/Karthikvenugopal/Multi-Source-Research-Analyst-Agent.git
cd Multi-Source-Research-Analyst-Agent

python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then add your keys
```

Required keys (both have free tiers): a [Tavily](https://tavily.com) key for web
search and a [Google AI Studio](https://aistudio.google.com/apikey) key for Gemini.

```bash
python app.py               # Gradio UI at http://localhost:7860
```

## Demo

![The agent planning its sources, streaming progress, and returning a cited report](docs/demo.gif)

Ask a research question; the agent plans its sources, retrieves them in parallel,
and returns a **cited** report — the inline `[n]` markers link down to a numbered,
clickable reference list. Real excerpt (*"What is retrieval-augmented generation
and why is it used?"*):

```text
## Research Report: Retrieval-Augmented Generation (RAG) — Definition, Purpose, and Applications

## Executive Summary
This report provides a comprehensive analysis of Retrieval-Augmented Generation
(RAG), a pivotal technique designed to enhance Large Language Models (LLMs). RAG
is consistently defined across sources as ...
```

The full report also includes **Key Findings** (themed, with confidence levels),
**Analysis** (agreements and conflicts across sources), **Limitations**, and
formatted **Sources**.

**Deploying:** it's a standard Gradio app and runs on **Hugging Face Spaces**
(`app.py` + `requirements.txt`). A public demo on a free Gemini key rate-limits
quickly (~20 req/day), so a recorded walkthrough is the more reliable portfolio
artifact.

## Testing

```bash
pip install -r requirements-dev.txt
pytest                      # 29 unit tests, fully mocked, < 1s
```

The suite mocks every external client (Tavily, Wikipedia, ArXiv, Gemini), so it
needs no API keys or network and runs in CI on every push.

## Roadmap

- **Expanded eval set** — grow `datasets/` and report per-category scores.
- **Result caching** — cache retrieval/LLM calls to make eval runs cheaper and faster.
- **Hosted demo** — deploy to Hugging Face Spaces with a recorded walkthrough.

## License

MIT — see [LICENSE](LICENSE).
