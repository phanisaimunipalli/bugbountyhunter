import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass, field

import git


@dataclass
class SandboxRunner:
    run_id: str
    sandbox_base: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "bh_sandbox")

    def __post_init__(self):
        self.sandbox_base = Path(self.sandbox_base)
        self.run_dir = self.sandbox_base / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def clone(self, repo_url: str) -> str:
        dest = self.run_dir / "repo"
        if dest.exists():
            shutil.rmtree(dest)
        git.Repo.clone_from(repo_url, str(dest), depth=1)
        return str(dest)

    def apply_patch(self, repo_path: str, patch_diff: str) -> None:
        patch_file = self.run_dir / "fix.patch"
        patch_file.write_text(patch_diff)
        result = subprocess.run(
            ["git", "apply", "--whitespace=fix", str(patch_file)],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"patch apply failed:\n{result.stderr}")

    def run_tests_in_dir(self, repo_path: str, timeout: int = 90) -> dict:
        venv_dir = self.run_dir / "venv"
        if not venv_dir.exists():
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

        pip = venv_dir / "bin" / "pip"
        python = venv_dir / "bin" / "python"

        repo = Path(repo_path)
        if (repo / "pyproject.toml").exists() or (repo / "setup.py").exists():
            subprocess.run(
                [str(pip), "install", "-e", ".[test,dev,testing]", "--quiet",
                 "--extra-index-url", "https://pypi.org/simple"],
                cwd=repo_path,
                capture_output=True,
                timeout=120,
            )
        else:
            subprocess.run(
                [str(pip), "install", "pytest", "--quiet"],
                capture_output=True,
            )

        result = subprocess.run(
            [str(python), "-m", "pytest", "--tb=short", "-q", repo_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        return {"passed": passed, "test_output": output}

    def cleanup(self) -> None:
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)
