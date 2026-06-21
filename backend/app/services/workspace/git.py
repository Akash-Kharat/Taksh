import subprocess
from pathlib import Path
from typing import Dict, Any, List
from app.core.config import settings
from app.core.logger import workspace_logger

class GitIntelligence:
    def __init__(self, workspace_dir: Path = None):
        self.workspace_dir = workspace_dir or settings.WORKSPACE_DIR

    def get_git_info(self) -> Dict[str, Any]:
        """
        Executes read-only git commands to fetch branch, status, and recent commits.
        Returns:
            dict containing:
                "branch": str
                "status": {"modified": [...], "staged": [...], "untracked": [...]}
                "recent_commits": [{"sha": "...", "author": "...", "message": "...", "date": "..."}]
        """
        cwd_path = Path(self.workspace_dir).resolve()
        if not cwd_path.exists() or not cwd_path.is_dir():
            workspace_logger.warning(f"Git path {cwd_path} does not exist or is not a directory.")
            return self._empty_git_info()

        # Check if it is a git repo first
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(cwd_path),
                capture_output=True,
                text=True,
                timeout=2
            )
            if res.returncode != 0 or "true" not in res.stdout.lower():
                return self._empty_git_info()
        except Exception as e:
            workspace_logger.warning(f"Failed to check if {cwd_path} is a git repository: {e}")
            return self._empty_git_info()

        branch = self._get_current_branch(cwd_path)
        status = self._get_status(cwd_path)
        commits = self._get_recent_commits(cwd_path)

        return {
            "branch": branch,
            "status": status,
            "recent_commits": commits
        }

    def _empty_git_info(self) -> Dict[str, Any]:
        return {
            "branch": "none",
            "status": {"modified": [], "staged": [], "untracked": []},
            "recent_commits": []
        }

    def _get_current_branch(self, cwd: Path) -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=2
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception as e:
            workspace_logger.warning(f"Error getting git branch: {e}")
        return "none"

    def _get_status(self, cwd: Path) -> Dict[str, List[str]]:
        status_info = {"modified": [], "staged": [], "untracked": []}
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=2
            )
            if res.returncode != 0:
                return status_info

            for line in res.stdout.splitlines():
                if len(line) < 4:
                    continue
                code = line[:2]
                filename = line[3:].strip()
                
                # Check untracked
                if code == "??":
                    status_info["untracked"].append(filename)
                else:
                    # Staged changes (Index column)
                    if code[0] in ["A", "M", "D", "R"]:
                        status_info["staged"].append(filename)
                    # Unstaged changes (Work tree column)
                    if code[1] in ["M", "D"]:
                        status_info["modified"].append(filename)

        except Exception as e:
            workspace_logger.warning(f"Error getting git status: {e}")
        return status_info

    def _get_recent_commits(self, cwd: Path) -> List[Dict[str, str]]:
        commits = []
        try:
            res = subprocess.run(
                ["git", "log", "-n", "5", "--pretty=format:%H|%an|%s|%ad", "--date=iso"],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=2
            )
            if res.returncode != 0:
                return commits

            for line in res.stdout.splitlines():
                parts = line.strip().split("|")
                if len(parts) >= 4:
                    commits.append({
                        "sha": parts[0],
                        "author": parts[1],
                        "message": "|".join(parts[2:-1]),  # Recombine message if it contained |
                        "date": parts[-1]
                    })
        except Exception as e:
            workspace_logger.warning(f"Error getting git commits: {e}")
        return commits
