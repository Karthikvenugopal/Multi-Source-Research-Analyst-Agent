# Multi-Source Research Analyst Agent

[![CI](https://github.com/Karthikvenugopal/Multi-Source-Research-Analyst-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Karthikvenugopal/Multi-Source-Research-Analyst-Agent/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

An autonomous research agent built with **LangGraph**. Given a question, it decides
which sources to consult (web, Wikipedia, academic papers), gathers evidence across
them, and synthesizes a single cited report — and its output quality is measured by
a model-graded evaluation harness rather than asserted.

## Highlights

- **Agentic control flow** — a supervisor node (LLM) repeatedly decides the next
  action (search a source / synthesize / finish) in a Reason → Act → Observe loop,
  with deterministic fallbacks so it never stalls.
- **Multi-source retrieval** — web search (Tavily), Wikipedia, and ArXiv, each
  normalized into a common finding schema with source attribution.
- **Measured, not asserted** — an LLM-as-judge scores every report on faithfulness,
  answer relevance, and citation coverage (see [Evaluation](#evaluation)).
- **Tested and CI-gated** — 27 hermetic unit tests (no network or API keys) run on
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

_Agent: `gemini-2.5-flash-lite` · Judge: `gemini-2.5-flash` (temperature 0) · 3 questions · **baseline, before query reformulation**._
_(Eval runs the agent on the cheaper flash-lite to stay within free-tier limits; the default agent model is `gemini-2.5-flash`.)_

| Question | Faithfulness | Relevance | Citations | Overall |
| --- | :---: | :---: | :---: | :---: |
| Factual — *what is RAG?* | 1.00 | 0.95 | 0.90 | **0.95** |
| Technical — *transformers & self-attention* | 0.30 | 0.10 | 0.50 | **0.30** |
| Comparative — *solar vs. wind energy* | 1.00 | 0.90 | 1.00 | **0.97** |
| **Mean** | **0.77** | **0.65** | **0.80** | **0.74** |

**What the eval surfaced:** the technical question scored poorly because the agent
currently sends the *full natural-language question* as the search query to every
source; for long questions this returns weak Wikipedia/ArXiv hits, so the report
can't ground its answer. This motivated **per-source query reformulation**, now
implemented: the supervisor emits a concise, source-tailored query in one
structured-output call (e.g. *"self-attention transformer architecture"* instead
of the full sentence), which already restores web retrieval on that question. A
clean re-scored before/after table is pending fresh free-tier quota.

## Architecture

```
          ┌──────────────┐   LLM decides the next action each loop
          │  Supervisor  │◀──────────────────────┐
          └──────┬───────┘                        │
                 │ route                           │
     ┌───────────┼────────────┐                   │
     ▼           ▼            ▼                    │
 ┌────────┐ ┌──────────┐ ┌────────┐               │
 │  Web   │ │Wikipedia │ │ ArXiv  │  findings ─────┘
 │(Tavily)│ │          │ │        │
 └────────┘ └──────────┘ └────────┘
                 │ enough / diverse evidence
                 ▼
          ┌──────────────┐      ┌──────────┐
          │  Synthesize  │ ───▶ │  Report  │ ───▶ cited report
          └──────────────┘      └──────────┘
```

| Module | Responsibility |
| --- | --- |
| `graph.py` | LangGraph state graph: nodes, edges, routing |
| `nodes.py` | Supervisor decision, per-source research, synthesis, report |
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

## Testing

```bash
pip install -r requirements-dev.txt
pytest                      # 27 unit tests, fully mocked, < 1s
```

The suite mocks every external client (Tavily, Wikipedia, ArXiv, Gemini), so it
needs no API keys or network and runs in CI on every push.

## Roadmap

- **Parallel retrieval** — fetch sources concurrently to cut latency and LLM calls.
- **Expanded eval set** — grow `datasets/` and report per-category scores.
- **Hosted demo** — deploy to Hugging Face Spaces with a recorded walkthrough.

## License

MIT — see [LICENSE](LICENSE).
