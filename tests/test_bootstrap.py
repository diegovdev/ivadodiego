"""Verify all package modules are importable."""

import importlib

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "museums",
        "museums.scraper",
        "museums.enricher",
        "museums.db",
        "museums.regression",
        "museums.api",
    ],
)
def test_module_importable(module: str) -> None:
    importlib.import_module(module)
