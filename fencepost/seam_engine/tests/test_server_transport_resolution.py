"""Task 647: seam_engine.server's `if __name__ == "__main__":` block read
`transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"` and handed that
bare `str` straight to `arcade_mcp_server.MCPApp.run(transport=...)`, whose
own `transport` parameter is typed `Literal["http", "stdio"]` -- mypy
--strict flagged the mismatch, and the block sat inside `__main__` so it
was never exercised by any test. Reproduced live before the fix:
`seam_engine.server bogus` registers all six tools, starts logging, and
only THEN raises `arcade_mcp_server.exceptions.ServerError: Invalid
transport: bogus`, burying the real problem under six "Added tool" lines
and a full traceback. The fix extracts `_resolve_transport(argv)`, a pure
function `app.run()` never has to be called to test, that validates the
CLI argument before any tool registration happens and exits with a single
clean usage line on an invalid value.
"""
from __future__ import annotations

import pytest

from seam_engine.server import _VALID_TRANSPORTS, _resolve_transport


def test_resolve_transport_defaults_to_stdio_with_no_argv():
    assert _resolve_transport(["seam_engine.server"]) == "stdio"


@pytest.mark.parametrize("transport", list(_VALID_TRANSPORTS))
def test_resolve_transport_accepts_every_valid_value(transport):
    assert _resolve_transport(["seam_engine.server", transport]) == transport


def test_resolve_transport_rejects_an_invalid_value_before_app_run():
    with pytest.raises(SystemExit) as exc_info:
        _resolve_transport(["seam_engine.server", "bogus"])
    message = str(exc_info.value)
    assert "bogus" in message
    assert "http" in message
    assert "stdio" in message
