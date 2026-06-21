import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from app.core.config import settings
from app.core.logger import workspace_logger

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".pytest_cache", ".taksh", ".gemini", ".vscode"
}

EXTENSION_TO_LANG = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".cpp": "C/C++",
    ".cc": "C/C++",
    ".cxx": "C/C++",
    ".h": "C/C++",
    ".hpp": "C/C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".md": "Markdown"
}

FRAMEWORK_SIGNATURES = {
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "react": "React",
    "vue": "Vue",
    "next": "Next.js",
    "express": "Express",
    "nest": "NestJS",
    "gin": "Gin",
    "axum": "Axum",
    "rocket": "Rocket"
}

class RepositoryScanner:
    def __init__(self, workspace_dir: Path = None):
        self.workspace_dir = workspace_dir or settings.WORKSPACE_DIR

    def scan(self) -> Tuple[List[Dict[str, Any]], List[str], bool]:
        """
        Scans the workspace directory.
        Returns:
            languages: List of dicts, e.g. [{"language": "Python", "file_count": 10}] sorted by count desc
            frameworks: List of strings of detected frameworks
            scan_limit_reached: bool indicating if limits were hit
        """
        root_path = Path(self.workspace_dir).resolve()
        if not root_path.exists() or not root_path.is_dir():
            workspace_logger.warning(f"Workspace path {root_path} does not exist or is not a directory.")
            return [], [], False

        workspace_logger.info(f"Scanning repository at: {root_path}")

        lang_counts = {}
        detected_frameworks = set()
        file_count = 0
        scan_limit_reached = False

        # We'll use os.walk to control depth manually
        for root, dirs, files in os.walk(root_path):
            # Calculate depth relative to root_path
            rel_path = os.path.relpath(root, root_path)
            depth = 0 if rel_path == "." else len(Path(rel_path).parts)

            # Check scan depth limit
            if depth >= settings.MAX_SCAN_DEPTH:
                # Don't scan subdirectories of this folder
                dirs.clear()
                scan_limit_reached = True
                continue

            # Modify dirs in-place to avoid walking ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                file_count += 1
                if file_count > settings.MAX_SCAN_FILES:
                    scan_limit_reached = True
                    break

                filepath = Path(root) / file
                ext = filepath.suffix.lower()

                # Language detection
                if ext in EXTENSION_TO_LANG:
                    lang = EXTENSION_TO_LANG[ext]
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

                # Framework detection via signature files
                filename = file.lower()
                if filename == "package.json":
                    self._detect_js_frameworks(filepath, detected_frameworks)
                elif filename in ["requirements.txt", "pipfile", "pyproject.toml", "setup.py"]:
                    self._detect_python_frameworks(filepath, detected_frameworks)
                elif filename == "go.mod":
                    self._detect_go_frameworks(filepath, detected_frameworks)
                elif filename == "cargo.toml":
                    self._detect_rust_frameworks(filepath, detected_frameworks)

            if file_count > settings.MAX_SCAN_FILES:
                break

        # Format languages sorted by count descending
        sorted_languages = [
            {"language": lang, "file_count": count}
            for lang, count in sorted(lang_counts.items(), key=lambda item: -item[1])
        ]
        
        # Enforce budget max frameworks (10)
        frameworks_list = sorted(list(detected_frameworks))[:settings.MAX_FRAMEWORKS]

        workspace_logger.info(f"Scan complete. Files scanned: {file_count}, Limit hit: {scan_limit_reached}, Frameworks: {frameworks_list}")
        return sorted_languages, frameworks_list, scan_limit_reached

    def _detect_js_frameworks(self, filepath: Path, detected_frameworks: set):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = json.load(f)
                deps = {**content.get("dependencies", {}), **content.get("devDependencies", {})}
                for dep in deps:
                    dep_lower = dep.lower()
                    for sig, framework in FRAMEWORK_SIGNATURES.items():
                        if sig in dep_lower:
                            detected_frameworks.add(framework)
        except Exception as e:
            workspace_logger.warning(f"Error parsing package.json at {filepath}: {e}")

    def _detect_python_frameworks(self, filepath: Path, detected_frameworks: set):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().lower()
                for sig, framework in FRAMEWORK_SIGNATURES.items():
                    if sig in content:
                        detected_frameworks.add(framework)
        except Exception as e:
            workspace_logger.warning(f"Error parsing python config at {filepath}: {e}")

    def _detect_go_frameworks(self, filepath: Path, detected_frameworks: set):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().lower()
                for sig, framework in FRAMEWORK_SIGNATURES.items():
                    if sig in content:
                        detected_frameworks.add(framework)
        except Exception as e:
            workspace_logger.warning(f"Error parsing go.mod at {filepath}: {e}")

    def _detect_rust_frameworks(self, filepath: Path, detected_frameworks: set):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().lower()
                for sig, framework in FRAMEWORK_SIGNATURES.items():
                    if sig in content:
                        detected_frameworks.add(framework)
        except Exception as e:
            workspace_logger.warning(f"Error parsing Cargo.toml at {filepath}: {e}")
