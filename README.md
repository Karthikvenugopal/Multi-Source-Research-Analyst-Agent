# Multi-Source Research Analyst Agent

[![CI](https://github.com/Karthikvenugopal/Multi-Source-Research-Analyst-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Karthikvenugopal/Multi-Source-Research-Analyst-Agent/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![Coverage gate](https://img.shields.io/badge/coverage-%E2%89%A575%25-0A9EDC)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A portfolio-scale prototype for bounded, iterative research across the web,
Wikipedia, and ArXiv. The default agent decides what to search, inspects evidence,
searches again when justified, and returns an evidence-ID-cited report only after
deterministic citation checks. The original single-pass pipeline remains available
as `legacy` mode for honest comparison.

This is not a legal research product, is not affiliated with Harvey, and does not
implement or reproduce Harvey's internal systems.

## The problem

The original project used a fixed path:

```text
question → plan once → gather once → synthesize → report
```

That baseline had several concrete limitations:

- The graph could not inspect a first result and issue a better second search.
- Retrieval failures were returned as low-confidence “findings.”
- Confidence was assigned from source type rather than evidence quality.
- Every source item was cut to a 200-character prefix for synthesis.
- Citations used positional numbers and were never checked against the evidence.
- State did not track attempted queries, gaps, conflicts, budgets, or stop reasons.
- Evaluation centered on one live LLM judge and only six dataset questions.

Single-pass retrieval is reasonable for a baseline, but it is weak for comparative,
multi-hop, technical, current, and conflicting-source questions. This redesign adds
bounded iterative retrieval without deleting that baseline.

## Legacy and agentic architectures

Legacy mode preserves the original LangGraph nodes:

```text
┌─────────┐    ┌─────────────┐    ┌────────────┐    ┌────────┐
│ Planner │ →  │ Gather once │ →  │ Synthesize │ →  │ Report │
└─────────┘    └─────────────┘    └────────────┘    └────────┘
                       Web · Wikipedia · ArXiv
```

Agentic mode moves source routing into a top-level model-directed loop. Source order
is not encoded in the runtime:

```text
User question
     │
     ▼
Requirements + research agent
     │
     ├── choose Tool Bundle + tailored query
     ├── inspect selected evidence passages
     ├── track gaps and likely conflicts
     └── repeat or stop
             │
             ▼
      Evidence-only report
             │
             ▼
  Deterministic citation verifier
       │                 │
     pass          one repair attempt
       │                 │
       └────── final report + warning if still invalid
```

The model decides whether another search is useful. Deterministic code enforces
maximum iterations, tool calls, per-tool timeouts, elapsed time, result limits,
duplicate-query blocking, context limits, and one citation-repair attempt.

## Tool Bundles

`ToolBundle` packages a capability name, source type, description, use/avoid
guidance, one or more callable tools, Pydantic input/output schemas, result and
timeout limits, and positive/negative evaluation cases. The registry exposes
bundle metadata to the model; adding a bundle does not change the core loop.

| Bundle | Provider | Appropriate use | Avoid as default for |
| --- | --- | --- | --- |
| `web` | Tavily | Recent events, products, companies, broad or changing facts | Stable definitions or paper-first research |
| `wikipedia` | Wikipedia | Definitions, history, entity and encyclopedic context | Breaking news, prices, primary research |
| `academic` | ArXiv | Papers, technical methods, science and ML | Basic facts or non-academic current events |

Academic queries pass through a deterministic query guard that removes common
question phrasing and caps the query at 12 technical terms. Bundle metadata is
delimited as capability data, and registration rejects common cross-tool control
instructions such as attempts to force unrelated tools to run.

## Evidence ledger and context management

Every accepted result is stored outside the model prompt with a stable ID:

```json
{
  "evidence_id": "E1",
  "source_type": "academic",
  "title": "...",
  "url": "...",
  "authors": [],
  "published_at": null,
  "retrieved_at": "...",
  "query": "transformer self-attention",
  "content": "full normalized source content",
  "content_hash": "sha256...",
  "relevance_score": null,
  "metadata": {"provider": "arxiv"}
}
```

Exact hashes and conservative fuzzy matching remove identical or substantially
identical items. Near-identical text with different numeric values is retained so
the conflict detector can inspect it. Provider scores remain metadata; they are not
converted into fake confidence.

The full ledger is never overwritten by summaries. For each decision and reporting
step, `EvidenceSelector` ranks items against the current question and open gaps,
selects relevant paragraphs or sentences, and applies configurable per-item and
total context limits. The result records selected IDs and IDs omitted due to context
limits. Final coverage reports four sets: retrieved, selected, cited, and not used.

## Deterministic evidence safeguards

The citation verifier parses evidence citations such as `[E1]` and checks:

- every cited ID exists in the ledger;
- the report generator was actually given that evidence;
- each citation has one canonical reference and each reference is cited;
- malformed, duplicate, unsupported, and orphaned citations;
- substantive paragraphs without inline evidence citations;
- deterministic citation coverage.

If a draft fails, the runtime gives the draft, selected ledger passages, and
structured verifier errors to one bounded repair call. It verifies the repaired
draft again. A remaining failure is returned with a visible warning; it is never
silently marked as verified.

`ConflictDetector` conservatively flags likely disagreements based on shared topic
terms plus incompatible dates, numeric values, negation, or directional language.
Both evidence items remain in the ledger and the conflict appears in the trace and
report. This is a pragmatic signal, not complete semantic contradiction detection.

When no usable evidence is available, agentic mode returns an explicit insufficient-
evidence response with the stop reason and missing source requirements. It does not
ask the report model to invent an answer.

## State, stopping, and observability

Agentic results include:

- original question, requirements, and subquestions;
- evidence ledger and evidence coverage;
- tool-call history and normalized attempted queries;
- unresolved gaps and detected conflicts;
- iteration/tool counts and approximate context usage;
- elapsed time and deterministic stop reason;
- report, structured verification result, and operational trace.

Stop reasons include `evidence_sufficient`, `tool_budget_exhausted`,
`iteration_limit`, `all_tools_failed`, `no_new_evidence`, and
`time_budget_exhausted`. Trace events contain tool, query, counts, new evidence IDs,
duplicates, gaps, conflicts, errors, retries, duration, and stop decision. They store
concise action summaries—not private model chain-of-thought—and redact common API
key/token patterns from tool errors.

## Concrete hermetic example

The fixture-backed comparison exercises this sequence without network access:

```text
Question: Which language did the creator of Python work on immediately before Python?

Iteration 1
  bundle: wikipedia
  query: Python Guido
  result: E1
  gap: the background source needs cross-source corroboration

Iteration 2
  bundle: web
  refined query: Python Guido corroborating evidence
  result: E2

Report excerpt:
  The fixture evidence addresses which language the creator of Python worked on
  immediately before Python [E1][E2].

Verification: passed
Stop reason: evidence_sufficient
```

This is an architecture example with deterministic fixture content, not a live
factual benchmark. Run it with the offline command below and inspect the full trace.

## Evaluation methodology

The dataset contains 24 questions across factual, technical, comparative, recent,
academic, multi-hop, ambiguous, conflicting, insufficient-evidence, one-source,
and multi-source categories. Each case can specify expected/forbidden bundles,
required retrieval topics, and answer/abstention/conflict behavior.

Hermetic evaluators cover:

- lexical answer-relevance and cited-evidence-overlap proxies;
- citation validity and citation coverage;
- tool-selection precision and recall;
- retrieval-topic coverage and source-specific query quality;
- conflict disclosure and correct abstention;
- calls, iterations, latency, repeated queries, and completion reason.

The lexical faithfulness and relevance metrics are transparent CI proxies, not
semantic entailment scores. Live model-graded evaluation remains separate in
`evals/run_eval.py` and is never required by the default test suite.

Capability gates use positive and negative fixtures attached to each bundle and a
leave-one-bundle-out check. Tests cover regressions such as academic routing on
simple facts, web guidance suppressing encyclopedic routing, verbose context
breaking citations, disabled bundles, and cross-tool instruction injection.

### Executed comparison

The committed report in [`evals/comparison/comparison.md`](evals/comparison/comparison.md)
was executed on all 24 questions using deterministic local source/model fixtures.
It validates architecture and metrics plumbing; it does not measure live retrieval
or live answer quality.

| Metric | Legacy | Agentic |
| --- | ---: | ---: |
| Deterministic cited-overlap proxy | 0.000 | 0.750 |
| Deterministic lexical relevance proxy | 0.351 | 0.792 |
| Citation validity | 0.000 | 1.000 |
| Citation coverage | 0.000 | 1.000 |
| Expected-tool recall | 1.000 | 1.000 |
| Average tool calls | 1.417 | 1.417 |
| Average iterations | 1.000 | 2.208 |

The legacy fixture intentionally uses the preserved positional `[1]` citation
contract, which the new evidence-ID verifier rejects. Agentic mode costs additional
inspection iterations. No live comparison was executed for this redesign, so this
README does not claim the new architecture improves live answer quality.

A separate one-question live smoke test was executed for “What is photosynthesis?”
with the configured Gemini and source clients. Agentic mode selected Wikipedia,
queried `photosynthesis`, collected `E1`, stopped with `evidence_sufficient` after
2 iterations and 1 tool call, and passed deterministic citation verification. This
was a connectivity/behavior smoke test, not a scored evaluation.

## Installation and configuration

```bash
git clone https://github.com/Karthikvenugopal/Multi-Source-Research-Analyst-Agent.git
cd Multi-Source-Research-Analyst-Agent
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Configure a supported LLM provider (`google`, `openai`, or experimental local
`huggingface`) and a Tavily key for live web research. Wikipedia and ArXiv do not
require API keys. See `.env.example` for all budget and context settings.

## Running the project

Gradio, agentic by default with a legacy selector:

```bash
python app.py
```

CLI modes:

```bash
python demo.py --mode legacy --question "What is photosynthesis?"
python demo.py --mode agentic --question "What is photosynthesis?"
python demo.py --mode agentic --question "..." --trace-json traces/run.json
```

No-network end-to-end smoke examples:

```bash
python demo.py --offline-fixtures --mode legacy --question "What is photosynthesis?"
python demo.py --offline-fixtures --mode agentic --question "What is photosynthesis?"
```

Tests and coverage gate:

```bash
pytest
pytest --cov=. --cov-report=term-missing --cov-fail-under=75
```

Comparison evaluation:

```bash
# Hermetic, all 24 cases; writes JSON and Markdown
python -m evals.compare_modes --offline-fixtures

# Live retrieval/model comparison; requires configured credentials
python -m evals.compare_modes --limit 3 --out evals/live-comparison

# Optional live judge for faithfulness and relevance
python -m evals.compare_modes --limit 3 --live-judge --judge-model gemini-2.5-flash
```

Single-mode live evaluation:

```bash
python -m evals.run_eval --mode agentic --limit 3 --out evals/live-agentic
python -m evals.run_eval --mode legacy --limit 3 --out evals/live-legacy
```

## Project layout

```text
agent/          model contracts, prompts, policies, runtime, state
tool_bundles/   bundle interface, registry, web, Wikipedia, academic
evidence/       models, ledger, passage selector, conflicts, citations
evals/          deterministic evaluators, capability gates, judge, comparison
datasets/       24-case evaluation set
tests/          hermetic external-client and end-to-end tests
graph.py        legacy LangGraph plus agentic-by-default mode facade
app.py          Gradio UI
demo.py         CLI and trace export
```

## Public engineering influences

Two public Harvey engineering articles motivated the general architectural
direction: [“How Agentic Search Unlocks Legal Research Intelligence at Harvey”](https://www.harvey.ai/blog/how-agentic-search-unlocks-legal-research-intelligence)
describes iterative source selection, query formulation, completeness checks, and
citation-backed synthesis; [“3 Principles That Helped us Scale Agent Development”](https://www.harvey.ai/blog/principles-that-helped-us-scale-agent-development)
describes top-level agents, capability-oriented Tool Bundles, and capability-level
leave-one-out evaluation gates.

This project applies those public ideas to a small general-purpose research agent.
Its evidence ledger, stable evidence IDs, deterministic citation/reference checks,
context-coverage accounting, conservative conflict signals, secret-redacted trace,
and bounded repair policy are original implementation choices for this repository.
No Harvey branding, private code, legal sources, benchmarks, or affiliation are used
or implied.

## Known limitations

- Citation verification detects structural and coverage failures; it does not prove
  that every cited sentence is semantically entailed by its source.
- Conflict detection is lexical and numeric, so it can miss paraphrased conflicts or
  flag values that describe different populations or dates.
- Model sufficiency and tool selection remain probabilistic in live mode.
- A Python thread timeout lets the runtime continue but cannot forcibly terminate an
  already-blocked third-party HTTP call.
- Wikipedia and ArXiv wrappers currently return aggregated text rather than canonical
  passage-level records for every underlying page or paper.
- The committed comparison is fixture-backed. Live scores depend on providers,
  source availability, model versions, and credentials and were not run here.
- This prototype reduces unsupported citation classes; it does not eliminate
  hallucinations and should not be treated as production-ready.

## License

MIT — see [`LICENSE`](LICENSE).
