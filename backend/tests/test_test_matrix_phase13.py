"""Phase 13 meta checks: test modules exist for each audited area."""

from pathlib import Path


def test_backend_modules_cover_audited_domains():
    root = Path(__file__).parent
    expected = [
        "test_auth.py",
        "test_agent_core.py",
        "test_agent_boundary.py",
        "test_tool_framework.py",
        "test_browser_integration.py",
        "test_browser_policy.py",
        "test_desktop_engine.py",
        "test_vision_engine.py",
        "test_memory.py",
        "test_safety.py",
        "test_safety_phase9.py",
        "test_workflow_phase10.py",
        "test_events_phase12.py",
        "test_e2e_phase13.py",
        "test_security_phase13.py",
        "test_task_access.py",
        "test_permissions.py",
        "test_migrations.py",
        "test_integration_postgres.py",
    ]
    missing = [name for name in expected if not (root / name).exists()]
    assert not missing, f"Missing test modules: {missing}"