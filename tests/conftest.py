"""Shared pytest configuration.

Registers the test markers used across the suite so `-m unit` / `-m integration`
work and unknown-marker warnings stay off (see rules/ecc/python/testing.md).
"""


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast, isolated unit test")
    config.addinivalue_line(
        "markers", "integration: cross-module / integration test")
