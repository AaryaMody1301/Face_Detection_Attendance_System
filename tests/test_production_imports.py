from src.core.runtime import application_import_self_test


def test_supported_application_surface_imports_cleanly():
    result = application_import_self_test()
    assert result["ok"] is True, result["modules"]
