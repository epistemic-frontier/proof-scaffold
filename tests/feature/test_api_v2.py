import pytest

from skfd.api_v2 import DepsView, ExportsView, UnitMeta


def test_exports_view_and_deps_view_error_paths() -> None:
    exports = ExportsView({"x": 1, "y": 2})
    assert len(exports) == 2
    assert set(iter(exports)) == {"x", "y"}
    assert exports.as_dict() == {"x": 1, "y": 2}

    metas = {"pkg-a": UnitMeta(dist_name="pkg-a", module_name="a", build_path=None)}
    deps = {"pkg-a": exports}
    dv = DepsView(deps=deps, metas=metas)

    with pytest.raises(KeyError):
        _ = dv["missing"]

    with pytest.raises(AttributeError):
        _ = dv.missing

