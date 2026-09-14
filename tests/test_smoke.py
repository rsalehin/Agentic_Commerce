"""P0-02 smoke tests: the workspace imports and runs on Python 3.12."""

import sys


def test_python_312() -> None:
    assert sys.version_info[:2] == (3, 12)


def test_packages_import() -> None:
    import agent
    import core
    import gateway
    import wallet

    for pkg in (gateway, agent, wallet, core):
        assert pkg.__doc__
