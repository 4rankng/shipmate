"""
Shipmate Plugin - Shared Scripts Module

This module provides portable path resolution for shipmate plugin scripts.
It works on any machine by dynamically resolving the script location.

Usage:
    from scripts import get_procedure_dir, get_scripts_dir, get_skill_dir

    scripts_dir = get_scripts_dir()
    skill_dir = get_skill_dir('run')
    reviewer_dir = get_procedure_dir('reviewer')
"""

import sys
from pathlib import Path


def get_plugin_root() -> Path:
    """
    Get the plugin root directory dynamically.

    This function resolves the plugin location by walking up from
    the current file location until it finds the plugin.json marker.

    Returns:
        Path: The plugin root directory
    """
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent

    # Walk up to find plugin root (contains plugin.json)
    for parent in [current_dir, *current_dir.parents]:
        if (parent / "plugin.json").exists():
            return parent

    # Fallback: use the scripts directory itself
    return current_dir


def get_scripts_dir() -> Path:
    """
    Get the scripts directory path.

    Returns:
        Path: The scripts directory
    """
    return get_plugin_root() / "scripts"


def get_skill_dir(skill_name: str) -> Path:
    """
    Get a skill directory path.

    Args:
        skill_name: Name of a public skill ('specify', 'run', or 'review')

    Returns:
        Path: The skill directory
    """
    return get_plugin_root() / "skills" / skill_name


def get_procedure_dir(procedure_name: str) -> Path:
    """Return the directory for one bundled, non-discoverable procedure."""
    return get_plugin_root() / "internal" / procedure_name


def setup_path():
    """
    Setup sys.path to include the scripts directory.
    Call this at the beginning of any script that needs shared modules.
    """
    scripts_dir = str(get_scripts_dir())
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


# Auto-setup on import
setup_path()
