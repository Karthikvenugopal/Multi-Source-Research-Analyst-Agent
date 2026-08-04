"""Registration and default construction for research bundles."""

from __future__ import annotations

from collections.abc import Iterable

from config import Config
from tool_bundles.academic import build_academic_bundle
from tool_bundles.base import BundleRegistrationError, ToolBundle
from tool_bundles.web import build_web_bundle
from tool_bundles.wikipedia import build_wikipedia_bundle
from tools import ResearchTools


class ToolBundleRegistry:
    """A runtime-extensible collection of independently described bundles."""

    def __init__(self, bundles: Iterable[ToolBundle] = ()) -> None:
        self._bundles: dict[str, ToolBundle] = {}
        for bundle in bundles:
            self.register(bundle)

    def register(self, bundle: ToolBundle) -> None:
        """Register a new bundle without changing the agent loop."""
        if bundle.name in self._bundles:
            raise BundleRegistrationError(f"duplicate bundle name: {bundle.name}")
        self._bundles[bundle.name] = bundle

    def get(self, name: str) -> ToolBundle | None:
        """Return a registered bundle, if enabled."""
        return self._bundles.get(name)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._bundles)

    @property
    def bundles(self) -> tuple[ToolBundle, ...]:
        return tuple(self._bundles.values())

    def prompt_catalog(self) -> str:
        """Return safe, delimited bundle metadata for model selection."""
        return "\n\n".join(bundle.prompt_description() for bundle in self._bundles.values())

    def without(self, *names: str) -> "ToolBundleRegistry":
        """Create a leave-one-or-more-out registry for regression evaluation."""
        disabled = set(names)
        return ToolBundleRegistry(
            bundle for bundle in self._bundles.values() if bundle.name not in disabled
        )


def build_default_registry(tools: ResearchTools | None = None) -> ToolBundleRegistry:
    """Build the default web, Wikipedia, and academic registry."""
    clients = tools or ResearchTools(
        web_limit=Config.WEB_RESULT_LIMIT,
        wikipedia_limit=Config.WIKIPEDIA_RESULT_LIMIT,
        arxiv_limit=Config.ARXIV_RESULT_LIMIT,
    )
    return ToolBundleRegistry((
        build_web_bundle(clients),
        build_wikipedia_bundle(clients),
        build_academic_bundle(clients),
    ))
