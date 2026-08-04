"""Schemas and interfaces for source-specific research bundles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, Field


class BundleQuery(BaseModel):
    """Validated input accepted by every research bundle."""

    query: str = Field(min_length=1, max_length=500)


class BundleOutput(BaseModel):
    """Validated, provider-neutral output from a bundle execution."""

    results: list[dict[str, Any]] = Field(default_factory=list)


@dataclass(frozen=True)
class EvaluationCase:
    """Capability fixture attached to a bundle."""

    question: str
    should_use: bool


@dataclass(frozen=True)
class BundleTool:
    """One callable exposed by a bundle."""

    name: str
    description: str
    callable: Callable[[str], list[dict[str, Any]]]


class BundleRegistrationError(ValueError):
    """Raised when bundle metadata is invalid or instruction-like content is unsafe."""


@dataclass(frozen=True)
class ToolBundle:
    """A source capability with instructions, schemas, limits, and eval cases."""

    name: str
    source_type: str
    description: str
    when_to_use: str
    when_not_to_use: str
    tools: tuple[BundleTool, ...]
    evaluation_cases: tuple[EvaluationCase, ...]
    result_limit: int = 5
    timeout_seconds: float = 20.0
    query_transform: Callable[[str], str] = field(default=lambda query: query)
    input_schema: type[BaseModel] = BundleQuery
    output_schema: type[BaseModel] = BundleOutput

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", self.name):
            raise BundleRegistrationError(f"invalid bundle name: {self.name!r}")
        if not self.tools:
            raise BundleRegistrationError(f"bundle {self.name!r} has no tools")
        instruction_text = f"{self.description} {self.when_to_use} {self.when_not_to_use}"
        suspicious = (
            r"ignore\s+(?:all\s+)?previous",
            r"always\s+call",
            r"must\s+(?:also\s+)?(?:call|use)\s+(?:web|wikipedia|academic)",
        )
        if any(re.search(pattern, instruction_text, re.IGNORECASE) for pattern in suspicious):
            raise BundleRegistrationError(
                f"bundle {self.name!r} contains cross-tool control instructions"
            )

    def prepare_query(self, query: str) -> str:
        """Validate and apply the source-specific query transformation."""
        validated = self.input_schema(query=" ".join(query.split()).strip())
        transformed = " ".join(self.query_transform(validated.query).split()).strip()
        if not transformed:
            transformed = validated.query
        return str(self.input_schema(query=transformed).query)

    def execute(self, query: str) -> BundleOutput:
        """Execute the bundle's primary tool and validate/cap its results."""
        tailored = self.prepare_query(query)
        results = self.tools[0].callable(tailored)
        return self.output_schema(results=list(results)[: max(1, self.result_limit)])

    def prompt_description(self) -> str:
        """Render metadata as quoted capability data, not executable instructions."""
        return (
            f"<bundle name=\"{self.name}\">\n"
            f"description: {self.description}\n"
            f"use_when: {self.when_to_use}\n"
            f"avoid_when: {self.when_not_to_use}\n"
            "</bundle>"
        )
