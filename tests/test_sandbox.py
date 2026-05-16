import os
import textwrap
from pathlib import Path

os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_run_tests_passes_for_valid_test(tmp_path):
    from sandbox.runner import SandboxRunner
    repo_dir = tmp_path / "fake_repo"
    repo_dir.mkdir()
    (repo_dir / "test_simple.py").write_text("def test_pass(): assert 1 == 1\n")

    runner = SandboxRunner(run_id="test-001", sandbox_base=tmp_path)
    result = runner.run_tests_in_dir(str(repo_dir))
    assert result["passed"] is True
    assert "1 passed" in result["test_output"]


def test_apply_patch_modifies_file(tmp_path):
    from sandbox.runner import SandboxRunner
    import subprocess
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    target = repo_dir / "foo.py"
    target.write_text("x = 1\n")

    # git apply requires a git repo
    subprocess.run(["git", "init"], cwd=str(repo_dir), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=test@test.com", "-c", "user.name=Test", "commit", "-m", "init"],
        cwd=str(repo_dir),
        capture_output=True,
    )

    patch = textwrap.dedent("""\
        --- a/foo.py
        +++ b/foo.py
        @@ -1 +1 @@
        -x = 1
        +x = 2
    """)
    runner = SandboxRunner(run_id="test-002", sandbox_base=tmp_path)
    runner.apply_patch(str(repo_dir), patch)
    assert target.read_text() == "x = 2\n"


def test_failed_tests_returns_passed_false(tmp_path):
    from sandbox.runner import SandboxRunner
    repo_dir = tmp_path / "bad_repo"
    repo_dir.mkdir()
    (repo_dir / "test_fail.py").write_text("def test_fail(): assert False\n")

    runner = SandboxRunner(run_id="test-003", sandbox_base=tmp_path)
    result = runner.run_tests_in_dir(str(repo_dir))
    assert result["passed"] is False
    assert "failed" in result["test_output"]
