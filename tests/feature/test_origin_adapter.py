from __future__ import annotations

import sys
from pathlib import Path

from skfd.builder.origin_adapter import InspectOriginAdapter
from skfd.core.origin import OriginTable


def test_origin_adapter_captures_the_requested_frame_without_stack_walk() -> None:
    table = OriginTable()
    adapter = InspectOriginAdapter(table, "test")

    expected_line = sys._getframe().f_lineno + 1
    origin = adapter.here_ref(depth=1)
    record = table.get(origin)

    assert Path(record.file) == Path(__file__)
    assert record.line == expected_line
