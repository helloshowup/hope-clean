"""Machine-readable Block Library specification and validation utilities."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, create_model, ValidationError
from .models import PlanModel

BLOCK_LIBRARY = {
    "lesson_metadata": {
        "fields": {
            "title": "str",
            "module_id": "str",
            "subtitle": "Optional[str]",
            "purpose": "Optional[str]",
        }
    },
    "learning_objectives": {
        "fields": {
            "objectives": "List[str]",
        }
    },
    "introduction": {
        "fields": {
            "content_summary": "str",
            "hook_suggestion": "Optional[str]",
        }
    },
    "section_heading": {
        "fields": {
            "level": "int",
            "title": "str",
        }
    },
    "explanatory_text": {
        "fields": {
            "topic": "str",
            "key_points": "List[str]",
            "tone_suggestion": "Optional[str]",
        }
    },
    "list_block": {
        "fields": {
            "list_type": "'numbered' | 'bulleted'",
            "heading": "Optional[str]",
            "items_summary": "List[str]",
        }
    },
    "example_analysis": {
        "fields": {
            "example_title": "str",
            "initial_statement": "str",
            "analysis_criteria": "List[str]",
            "improved_version_summary": "str",
            "explanation_points": "List[str]",
        }
    },
    "process_steps": {
        "fields": {
            "process_name": "str",
            "introductory_text": "Optional[str]",
            "steps": "List[Dict[str, str]]",
        }
    },
    "reflection_prompt": {
        "fields": {
            "prompt_heading": "str",
            "questions": "List[str]",
            "context_setting": "Optional[str]",
        }
    },
    "key_takeaways": {
        "fields": {
            "points": "List[str]",
        }
    },
    "diagram_placeholder": {
        "fields": {
            "concept_to_illustrate": "str",
            "description": "str",
            "caption": "Optional[str]",
            "placement_suggestion": "Optional[str]",
        }
    },
    "flowchart_placeholder": {
        "fields": {
            "process_name": "str",
            "description": "str",
            "caption": "Optional[str]",
            "placement_suggestion": "Optional[str]",
        }
    },
    "image_placeholder": {
        "fields": {
            "description": "str",
            "caption": "Optional[str]",
            "placement_suggestion": "Optional[str]",
        }
    },
}


def get_block_type_definitions() -> str:
    """Return block definitions as a compact type description."""
    lines = []
    for name, info in BLOCK_LIBRARY.items():
        fields = info["fields"]
        field_str = ", ".join(f"{k}: {v}" for k, v in fields.items())
        lines.append(f"- **{name}**: {{ {field_str} }}")
    return "\n".join(lines)


def _parse_type(type_str: str):
    """Return a Python type object from a simple string description."""
    type_str = type_str.strip()
    optional = False
    if type_str.startswith("Optional[") and type_str.endswith("]"):
        optional = True
        type_str = type_str[len("Optional["):-1]

    # handle union like 'numbered' | 'bulleted'
    if "|" in type_str and "'" in type_str:
        # treat simple union of string literals as plain str
        py_type = str
    elif type_str.startswith("List[") and type_str.endswith("]"):
        inner = _parse_type(type_str[len("List["):-1])
        py_type = List[inner]  # type: ignore[arg-type]
    elif type_str.startswith("Dict[") and type_str.endswith("]"):
        py_type = Dict[str, str]
    else:
        mapping = {"str": str, "int": int, "float": float, "bool": bool}
        py_type = mapping.get(type_str, Any)

    if optional:
        return Optional[py_type]
    return py_type


def build_pydantic_models():
    """Create Pydantic models for each block type and the overall plan."""
    models = {}
    for block_name, info in BLOCK_LIBRARY.items():
        fields = {"block_type": (str, ...)}
        for fname, ftype in info["fields"].items():
            py_type = _parse_type(ftype)
            default = ...
            if getattr(py_type, "__origin__", None) is Union and type(None) in py_type.__args__:
                default = None
                py_type = [a for a in py_type.__args__ if a is not type(None)][0]
            fields[fname] = (py_type, default)
        model = create_model(block_name.title().replace("_", ""), **fields)
        models[block_name] = model

    BlockUnion = Union[tuple(models.values())]
    PlanModel = create_model(
        "PlanModel",
        content_blocks=(List[BlockUnion], ...),
    )

    return models, PlanModel


BLOCK_MODELS, _ = build_pydantic_models()


def validate_plan(data: str | dict):
    """Validate a plan JSON string or object."""
    try:
        if isinstance(data, str):
            return PlanModel.model_validate_json(data)
        return PlanModel.model_validate(data)
    except ValidationError as e:
        raise ValueError(str(e))

