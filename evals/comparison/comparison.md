# Legacy versus agentic comparison

_Generated 2026-08-04T16:58:33+00:00 · hermetic fixture architecture benchmark; no live retrieval or model grading · 24 questions._

Faithfulness and relevance are deterministic lexical proxies unless the label explicitly says a live model judge was used.

| Metric | Legacy | Agentic |
| --- | ---: | ---: |
| Faithfulness | 0.000 | 0.750 |
| Answer Relevance | 0.351 | 0.792 |
| Citation Validity | 0.000 | 1.000 |
| Citation Coverage | 0.000 | 1.000 |
| Tool Selection Recall | 1.000 | 1.000 |
| Tool Calls | 1.417 | 1.417 |
| Iterations | 1.000 | 2.208 |
| Latency S | 0.000 | 0.000 |

## Per question

| ID | Category | Mode | Faithfulness | Relevance | Citations valid | Tool recall | Calls | Iterations | Stop reason |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| q01 | factual | legacy | 0.00 | 1.00 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q01 | factual | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q02 | factual | legacy | 0.00 | 0.50 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q02 | factual | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q03 | technical | legacy | 0.00 | 0.43 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q03 | technical | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q04 | academic | legacy | 0.00 | 0.14 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q04 | academic | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q05 | comparative | legacy | 0.00 | 0.29 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q05 | comparative | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 2 | 3 | evidence_sufficient |
| q06 | recent_information | legacy | 0.00 | 0.14 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q06 | recent_information | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q07 | recent_information | legacy | 0.00 | 0.38 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q07 | recent_information | agentic | 0.00 | 0.00 | 1.00 | 1.00 | 1 | 1 | no_new_evidence |
| q08 | multi_hop | legacy | 0.00 | 0.14 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q08 | multi_hop | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 2 | 3 | evidence_sufficient |
| q09 | ambiguous | legacy | 0.00 | 1.00 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q09 | ambiguous | agentic | 0.00 | 0.00 | 1.00 | 1.00 | 1 | 1 | no_new_evidence |
| q10 | conflicting_evidence | legacy | 0.00 | 0.40 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q10 | conflicting_evidence | agentic | 0.50 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q11 | insufficient_evidence | legacy | 0.00 | 0.20 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q11 | insufficient_evidence | agentic | 0.00 | 0.00 | 1.00 | 1.00 | 2 | 2 | no_new_evidence |
| q12 | single_source | legacy | 0.00 | 0.50 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q12 | single_source | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q13 | single_source | legacy | 0.00 | 0.17 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q13 | single_source | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q14 | multi_source | legacy | 0.00 | 0.12 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q14 | multi_source | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 2 | 3 | evidence_sufficient |
| q15 | comparative | legacy | 0.00 | 0.33 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q15 | comparative | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 2 | 3 | evidence_sufficient |
| q16 | historical | legacy | 0.00 | 0.40 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q16 | historical | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q17 | current_science | legacy | 0.00 | 0.43 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q17 | current_science | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 2 | 3 | evidence_sufficient |
| q18 | technical | legacy | 0.00 | 0.12 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q18 | technical | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 2 | 3 | evidence_sufficient |
| q19 | conflicting_evidence | legacy | 0.00 | 0.33 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q19 | conflicting_evidence | agentic | 0.50 | 1.00 | 1.00 | 1.00 | 2 | 3 | evidence_sufficient |
| q20 | multi_hop | legacy | 0.00 | 0.25 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q20 | multi_hop | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 2 | 3 | evidence_sufficient |
| q21 | recent_company | legacy | 0.00 | 0.14 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q21 | recent_company | agentic | 0.00 | 0.00 | 1.00 | 1.00 | 1 | 1 | no_new_evidence |
| q22 | factual | legacy | 0.00 | 0.29 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q22 | factual | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q23 | academic_comparative | legacy | 0.00 | 0.43 | 0.00 | 1.00 | 1 | 1 | legacy_completed |
| q23 | academic_comparative | agentic | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 2 | evidence_sufficient |
| q24 | insufficient_evidence | legacy | 0.00 | 0.29 | 0.00 | 1.00 | 2 | 1 | legacy_completed |
| q24 | insufficient_evidence | agentic | 0.00 | 0.00 | 1.00 | 1.00 | 2 | 2 | no_new_evidence |
