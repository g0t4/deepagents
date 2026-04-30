"""Dump the effective deepagents-cli configuration.

Similar to ``git config --list``, this module reads all config sources
(config.toml, environment variables, and runtime settings) and renders
them in a human-readable table or as machine-readable JSON.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from deepagents_cli._env_vars import (
    AUTO_UPDATE,
    DEBUG,
    DEBUG_FILE,
    EXTRA_SKILLS_DIRS,
    KITTY_KEYBOARD,
    LANGSMITH_PROJECT,
    NO_UPDATE_CHECK,
    SHELL_ALLOW_LIST,
    USER_ID,
)
from deepagents_cli._version import __version__
from deepagents_cli.config import (
    _GLOBAL_DOTENV_PATH,
    console,
    settings,
)
from deepagents_cli.model_config import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_CONFIG_PATH,
    ModelConfig,
)


def _dump_text() -> None:
    """Print the full config dump in a human-readable table format."""
    config = ModelConfig.load()

    _print_section("=== Config file ===")
    _print_config_file_section(config)

    _print_section("=== Environment variables ===")
    _print_env_vars_section()

    _print_section("=== Runtime settings ===")
    _print_settings_section()

    _print_section("=== Paths ===")
    _print_paths_section()


def _dump_json() -> dict[str, Any]:
    """Return the full config dump as a serialisable dict."""
    config = ModelConfig.load()
    return {
        "cli_version": __version__,
        "config_file": _config_file_to_dict(config),
        "env_vars": _env_vars_to_dict(),
        "settings": _settings_to_dict(),
        "paths": _paths_to_dict(),
    }


def dump_config(*, output_format: str = "text") -> None:
    """Dump the effective deepagents-cli configuration.

    Reads config.toml, environment variables, and runtime settings, then
    renders them as human-readable text or JSON.

    Args:
        output_format: Either ``"text"`` or ``"json"``.
    """
    if output_format == "json":
        envelope = {"schema_version": 1, "command": "config dump", "data": _dump_json()}
        sys.stdout.write(json.dumps(envelope, default=str) + "\n")
        sys.stdout.flush()
    else:
        _dump_text()


# ---------------------------------------------------------------------------
# Config file section
# ---------------------------------------------------------------------------


def _print_config_file_section(config: ModelConfig) -> None:
    """Print the config.toml-derived settings."""
    default_model = config.default_model or "(not set)"
    recent_model = config.recent_model or "(not set)"

    _print_kv("models.default", default_model)
    _print_kv("models.recent", recent_model)

    # Providers
    providers = config.providers
    if not providers:
        _print_kv("models.providers", "(none)")
    else:
        for name, provider in sorted(providers.items()):
            models = provider.get("models", [])
            model_str = ", ".join(models) if models else "(auto-discovered)"
            api_key_env = provider.get("api_key_env")
            base_url = provider.get("base_url")
            enabled = provider.get("enabled", True)

            _print_kv(f"providers.{name}.models", model_str)
            if api_key_env:
                _print_kv(f"providers.{name}.api_key_env", api_key_env)
            if base_url:
                _print_kv(f"providers.{name}.base_url", base_url)
            if not enabled:
                _print_kv(f"providers.{name}.enabled", "false")


def _config_file_to_dict(config: ModelConfig) -> dict[str, Any]:
    """Convert config file data to a dict for JSON output.

    Returns:
        Dict with ``default``, ``recent``, and ``providers`` keys.
    """
    result: dict[str, Any] = {
        "default": config.default_model,
        "recent": config.recent_model,
    }
    providers = {}
    for name, provider in sorted(config.providers.items()):
        providers[name] = {
            "models": provider.get("models", []),
            "api_key_env": provider.get("api_key_env"),
            "base_url": provider.get("base_url"),
            "enabled": provider.get("enabled", True),
        }
    result["providers"] = providers
    return result


# ---------------------------------------------------------------------------
# Environment variables section
# ---------------------------------------------------------------------------

# API-key env vars we report the *presence* (not the value) of.
_API_KEY_VARS: list[str] = [
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "COHERE_API_KEY",
    "DEEPSEEK_API_KEY",
    "FIREWORKS_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_CLOUD_PROJECT",
    "GROQ_API_KEY",
    "HUGGINGFACEHUB_API_TOKEN",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "LITELLM_API_KEY",
    "MISTRAL_API_KEY",
    "NVIDIA_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "PPLX_API_KEY",
    "TOGETHER_API_KEY",
    "TAVILY_API_KEY",
    "WATSONX_APIKEY",
    "XAI_API_KEY",
]

# CLI env var names — use the _env_vars constants so the drift test passes.
# Each constant's value is the full "DEEPAGENTS_CLI_..." name.
_DEEPAGENTS_CLI_ENV_VARS: list[str] = [
    AUTO_UPDATE,
    DEBUG,
    DEBUG_FILE,
    EXTRA_SKILLS_DIRS,
    KITTY_KEYBOARD,
    LANGSMITH_PROJECT,
    NO_UPDATE_CHECK,
    SHELL_ALLOW_LIST,
    USER_ID,
]


def _print_env_vars_section() -> None:
    """Print API key presence and DEEPAGENTS_CLI env vars."""
    # API keys
    _print_section_header("API Keys")
    for var in _API_KEY_VARS:
        present = os.environ.get(var) is not None
        prefix = "set" if present else "(unset)"
        _print_kv(var, prefix)

    # DEEPAGENTS_CLI_* vars
    _print_section_header("DEEPAGENTS_CLI_*")
    for var in _DEEPAGENTS_CLI_ENV_VARS:
        value = os.environ.get(var)
        if value:
            _print_kv(var, value)
        else:
            _print_kv(var, "(not set)")

    # dotenv files
    _print_section_header("Dotenv Files")
    project_dotenv = None
    try:
        from deepagents_cli.config import _find_dotenv_from_start_path

        project_dotenv = _find_dotenv_from_start_path(Path.cwd())
    except OSError:  # permission/path errors on CWD
        pass

    project_exists = "found" if project_dotenv else "not found"
    _print_kv("project .env (CWD)", project_exists)
    if project_dotenv:
        _print_kv("project .env path", str(project_dotenv))

    global_exists = "found" if _GLOBAL_DOTENV_PATH.exists() else "not found"
    _print_kv("global .env (~/.deepagents/.env)", global_exists)


def _env_vars_to_dict() -> dict[str, Any]:
    """Convert env vars to a dict for JSON output.

    Returns:
        Dict with ``api_keys``, ``cli_env_vars``, and ``dotenv`` keys.
    """
    api_keys = {}
    for var in _API_KEY_VARS:
        api_keys[var] = os.environ.get(var) is not None

    cli_env = {}
    for var in _DEEPAGENTS_CLI_ENV_VARS:
        value = os.environ.get(var)
        if value:
            cli_env[var] = value

    dotenv: dict[str, Any] = {}
    try:
        from deepagents_cli.config import _find_dotenv_from_start_path

        project_dotenv = _find_dotenv_from_start_path(Path.cwd())
        dotenv["project"] = {
            "exists": project_dotenv is not None,
            "path": str(project_dotenv) if project_dotenv else None,
        }
    except OSError:  # permission/path errors on CWD
        dotenv["project"] = {"exists": False, "path": None}

    dotenv["global"] = {
        "exists": _GLOBAL_DOTENV_PATH.exists(),
        "path": str(_GLOBAL_DOTENV_PATH),
    }

    return {"api_keys": api_keys, "cli_env_vars": cli_env, "dotenv": dotenv}


# ---------------------------------------------------------------------------
# Runtime settings section
# ---------------------------------------------------------------------------


def _print_settings_section() -> None:
    """Print runtime settings derived from the Settings singleton."""
    _print_section_header("API Keys")
    _print_kv("openai", "configured" if settings.openai_api_key else "not configured")
    _print_kv(
        "anthropic", "configured" if settings.anthropic_api_key else "not configured"
    )
    _print_kv("google", "configured" if settings.google_api_key else "not configured")
    _print_kv("nvidia", "configured" if settings.nvidia_api_key else "not configured")
    _print_kv("tavily", "configured" if settings.tavily_api_key else "not configured")
    _print_kv(
        "google_cloud_project",
        settings.google_cloud_project or "(not set)",
    )

    _print_section_header("LangSmith")
    _print_kv(
        "langsmith_project",
        settings.deepagents_langchain_project or "(not set)",
    )
    original = settings.user_langchain_project
    _print_kv("langsmith_project_original", original or "(not set)")

    _print_section_header("Model")
    _print_kv("model", settings.model_name or "(not set)")
    _print_kv("model_provider", settings.model_provider or "(not set)")
    if settings.model_context_limit:
        _print_kv("model_context_limit", str(settings.model_context_limit))

    _print_section_header("Project")
    _print_kv(
        "project_root",
        str(settings.project_root) if settings.project_root else "(not in a project)",
    )
    if settings.shell_allow_list:
        _print_kv(
            "shell_allow_list",
            ", ".join(settings.shell_allow_list),
        )
    else:
        _print_kv("shell_allow_list", "(not set)")

    if settings.extra_skills_dirs:
        dirs = ", ".join(str(d) for d in settings.extra_skills_dirs)
        _print_kv("extra_skills_dirs", dirs)
    else:
        _print_kv("extra_skills_dirs", "(not set)")


def _settings_to_dict() -> dict[str, Any]:
    """Convert runtime settings to a dict for JSON output.

    Returns:
        Dict with ``api_keys``, ``langsmith``, ``model``, and ``project`` keys.
    """
    result: dict[str, Any] = {
        "api_keys": {
            "openai": settings.openai_api_key is not None,
            "anthropic": settings.anthropic_api_key is not None,
            "google": settings.google_api_key is not None,
            "nvidia": settings.nvidia_api_key is not None,
            "tavily": settings.tavily_api_key is not None,
            "google_cloud_project": settings.google_cloud_project,
        },
        "langsmith": {
            "project": settings.deepagents_langchain_project,
            "project_original": settings.user_langchain_project,
        },
        "model": {
            "name": settings.model_name,
            "provider": settings.model_provider,
            "context_limit": settings.model_context_limit,
        },
        "project": {
            "root": str(settings.project_root) if settings.project_root else None,
            "shell_allow_list": settings.shell_allow_list,
            "extra_skills_dirs": (
                [str(d) for d in settings.extra_skills_dirs]
                if settings.extra_skills_dirs
                else None
            ),
        },
    }
    return result


# ---------------------------------------------------------------------------
# Paths section
# ---------------------------------------------------------------------------


def _print_paths_section() -> None:
    """Print key filesystem paths."""
    _print_kv("config_file", str(DEFAULT_CONFIG_PATH))
    _print_kv("config_dir", str(DEFAULT_CONFIG_DIR))
    _print_kv("global .env", str(_GLOBAL_DOTENV_PATH))
    _print_kv("user agents dir", str(settings.user_agents_dir))
    _print_kv("user .deepagents dir", str(settings.user_deepagents_dir))
    if settings.project_root:
        _print_kv(
            "project .deepagents dir",
            str(settings.project_root / ".deepagents"),
        )
        _print_kv(
            "project .agents dir",
            str(settings.project_root / ".agents"),
        )


def _paths_to_dict() -> dict[str, Any]:
    """Convert paths to a dict for JSON output.

    Returns:
        Dict with filesystem path entries.
    """
    root = settings.project_root
    return {
        "config_file": str(DEFAULT_CONFIG_PATH),
        "config_dir": str(DEFAULT_CONFIG_DIR),
        "global_dotenv": str(_GLOBAL_DOTENV_PATH),
        "user_agents_dir": str(settings.user_agents_dir),
        "user_deepagents_dir": str(settings.user_deepagents_dir),
        "project_deepagents_dir": (str(root / ".deepagents") if root else None),
        "project_agents_dir": (str(root / ".agents") if root else None),
    }


# ---------------------------------------------------------------------------
# Text rendering helpers
# ---------------------------------------------------------------------------


def _print_section(title: str) -> None:
    """Print a section header."""
    console.print()
    console.print(f"[bold]{title}[/bold]")
    console.print(f"{'=' * len(title)}")


def _print_section_header(title: str) -> None:
    """Print a subsection header."""
    console.print(f"\n[underline]{title}[/underline]")


def _print_kv(key: str, value: object) -> None:
    """Print a key-value pair in a compact column format."""
    console.print(f"  {key:35s} {value}")
