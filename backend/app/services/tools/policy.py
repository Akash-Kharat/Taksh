"""
Execution Policy Layer (MS-11)

Centralizes security rules including:
1. Executable whitelist verification.
2. Argument restrictions (Git allowed subcommands, Pytest arg count/depth/flags).
3. Directory validation (sandbox boundaries).
4. Explicit shell prohibition checks.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from app.core.config import settings


class ExecutionPolicy:
    """Centralizes command, argument, directory, and capability level validations."""

    ALLOWED_GIT_COMMANDS = set(settings.ALLOWED_GIT_COMMANDS)
    BANNED_GIT_COMMANDS = {"commit", "push", "pull", "reset", "clean", "checkout", "merge", "rebase", "init", "clone"}
    
    ALLOWED_PYTEST_FLAGS = {"-v", "--verbose", "-q", "--quiet", "-k"}

    @classmethod
    def validate_sandbox_cwd(cls, cwd: Path) -> Path:
        """
        Verify that the requested working directory resides within the workspace boundary.
        Returns the resolved absolute Path or raises PermissionError.
        """
        workspace = settings.WORKSPACE_DIR.resolve()
        resolved_cwd = cwd.resolve()
        try:
            resolved_cwd.relative_to(workspace)
        except ValueError:
            raise PermissionError(
                f"Directory validation failed: '{cwd}' resolves outside workspace boundary."
            )
        return resolved_cwd

    @classmethod
    def validate_executable(cls, executable_key: str) -> str:
        """
        Validates the executable key against the whitelist and returns its absolute path.
        Raises PermissionError if the binary is not allowed or cannot be resolved.
        """
        # Whitelist keys mapping to executable names
        executable_map = {
            "git": ["git", "git.exe"],
            "pytest": ["pytest", "pytest.exe"],
            "ruff": ["ruff", "ruff.exe"]
        }

        if executable_key not in executable_map:
            raise PermissionError(
                f"Executable validation failed: '{executable_key}' is not in the whitelist."
            )

        names = executable_map[executable_key]
        resolved_path = None
        for name in names:
            found = shutil.which(name)
            if found:
                resolved_path = found
                break

        if not resolved_path:
            raise PermissionError(
                f"Executable validation failed: Binary for '{executable_key}' could not be resolved on the system path."
            )

        return resolved_path

    @classmethod
    def validate_arguments(cls, executable_key: str, args: List[str]) -> None:
        """
        Validates argument arrays to prevent command injection and unauthorized usage.
        Raises ValueError if invalid argument patterns are found.
        """
        # Validate shell prohibition (ensure args are not nested commands or contain shell symbols)
        shell_symbols = [";", "&&", "||", "|", ">", "<", "`", "$", "(", ")"]
        for arg in args:
            if any(symbol in arg for symbol in shell_symbols):
                raise ValueError(
                    f"Shell characters detected in argument: '{arg}'. Shell operations are prohibited."
                )

        if executable_key == "git":
            cls._validate_git_args(args)
        elif executable_key == "pytest":
            cls._validate_pytest_args(args)
        elif executable_key == "ruff":
            cls._validate_ruff_args(args)

    @classmethod
    def _validate_git_args(cls, args: List[str]) -> None:
        # Find the first argument that is a subcommand (not a flag starting with -)
        subcommand = None
        for arg in args:
            if not arg.startswith("-"):
                subcommand = arg
                break

            # Prevent options that alter command execution (like --exec-path or alias definition)
            if arg.startswith("--exec-path") or arg.startswith("--alias"):
                raise ValueError(f"Prohibited git option detected: '{arg}'")

        if not subcommand:
            raise ValueError("Git subcommand could not be determined.")

        if subcommand in cls.BANNED_GIT_COMMANDS or subcommand not in cls.ALLOWED_GIT_COMMANDS:
            raise ValueError(
                f"Git subcommand '{subcommand}' is prohibited. Only {settings.ALLOWED_GIT_COMMANDS} are allowed."
            )

        # Scrape all args for banned commands just in case they are nested or passed as flags
        for arg in args:
            if arg in cls.BANNED_GIT_COMMANDS:
                raise ValueError(f"Prohibited Git subcommand detected in arguments: '{arg}'")

    @classmethod
    def _validate_pytest_args(cls, args: List[str]) -> None:
        # 1. Check max argument count
        if len(args) > settings.MAX_PYTEST_ARGUMENTS:
            raise ValueError(
                f"Pytest arguments count ({len(args)}) exceeds maximum limit of {settings.MAX_PYTEST_ARGUMENTS}."
            )

        # 2. Check for banned flags and path depths
        for arg in args:
            if arg.startswith("-"):
                # Ensure the flag itself is in the safe whitelist
                # If it starts with -k, it could be "-k" followed by an expression or "-k expr"
                if arg.startswith("-k"):
                    continue
                if arg not in cls.ALLOWED_PYTEST_FLAGS:
                    raise ValueError(f"Prohibited Pytest flag detected: '{arg}'")
            else:
                # Path argument - check depth
                path_obj = Path(arg)
                if len(path_obj.parts) > settings.MAX_TEST_PATH_DEPTH:
                    raise ValueError(
                        f"Test path depth of '{arg}' exceeds maximum depth of {settings.MAX_TEST_PATH_DEPTH}."
                    )
                # Check for traversal
                try:
                    Path(settings.WORKSPACE_DIR / arg).resolve().relative_to(settings.WORKSPACE_DIR.resolve())
                except ValueError:
                    raise ValueError(f"Path traversal detected in Pytest target: '{arg}'")

    @classmethod
    def _validate_ruff_args(cls, args: List[str]) -> None:
        # Ensure ruff runs only check/lint, and no fix flags are passed
        for arg in args:
            if arg == "--fix" or arg == "--fix-only":
                raise ValueError("Ruff file modification (--fix) is prohibited.")
            if arg.startswith("-") and arg not in {"-v", "--verbose", "-q", "--quiet", "--format", "--show-source", "--config"}:
                # If passing format or config, let it proceed but restrict general command injection
                if not any(arg.startswith(x) for x in {"--format", "--config", "--select", "--ignore"}):
                    raise ValueError(f"Prohibited Ruff option detected: '{arg}'")
