# Centralized session-state key builders
# This removes string duplication and prevents bugs

def get_qkey(category: str, concept: str) -> str:
    return f"{category}::{concept}"

def get_override_key(category: str, concept: str) -> str:
    return f"override::{category}::{concept}"

def get_override_level_key(category: str, concept: str) -> str:
    return f"override_level::{category}::{concept}"

def get_help_key(category: str, concept: str, item: str) -> str:
    return f"help::{category}::{concept}::{item}"

def get_none_key(category: str, concept: str) -> str:
    return f"help::{category}::{concept}::none"
