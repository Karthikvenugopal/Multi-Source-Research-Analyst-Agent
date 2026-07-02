"""Shared test setup.

Dummy credentials so that any incidental object construction succeeds. The unit
tests never make real network calls — every external client is mocked — so these
values are never used to authenticate anything.
"""
import os

os.environ.setdefault("TAVILY_API_KEY", "test-dummy")
os.environ.setdefault("GOOGLE_API_KEY", "test-dummy")
os.environ.setdefault("LLM_PROVIDER", "google")
os.environ.setdefault("LLM_MODEL", "gemini-2.5-flash")
