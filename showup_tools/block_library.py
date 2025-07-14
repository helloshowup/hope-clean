"""Machine-readable Block Library specification and validation utilities."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Literal, Annotated
import json

from pydantic import BaseModel, Field, create_model, ValidationError

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
        }
    },
    "flowchart_placeholder": {
        "fields": {
            "process_name": "str",
            "description": "str",
        }
    },
    "image_placeholder": {
        "fields": {
            "description": "str",
            "caption": "Optional[str]",
        }
    },
    "audio_placeholder": {
        "fields": {
            "topic": "str",
            "description": "str",
            "suggested_duration_seconds": "Optional[int]",
            "caption": "Optional[str]",
            "placement_suggestion": "Optional[str]",
        }
    },
    "video_placeholder": {
        "fields": {
            "topic": "str",
            "description": "str",
            "suggested_duration_seconds": "int",
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
        # parse union of string literals into Literal
        options = [part.strip().strip("'") for part in type_str.split("|")]
        py_type = Literal[tuple(options)]  # type: ignore[arg-type]
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
        fields = {"block_type": (Literal[block_name], block_name)}
        for fname, ftype in info["fields"].items():
            py_type = _parse_type(ftype)
            default = ...
            if getattr(py_type, "__origin__", None) is Union and type(None) in py_type.__args__:
                default = None
                py_type = [a for a in py_type.__args__ if a is not type(None)][0]
            fields[fname] = (py_type, default)
        model = create_model(block_name.title().replace("_", ""), **fields)
        models[block_name] = model

    BlockUnion = Annotated[
        Union[tuple(models.values())],
        Field(discriminator="block_type")
    ]
    PlanModel = create_model(
        "PlanModel",
        content_title=(str, ...),
        target_audience=(str, ...),
        estimated_word_count=(int, ...),
        content_blocks=(List[BlockUnion], ...),
    )

    return models, PlanModel


BLOCK_MODELS, PlanModel = build_pydantic_models()


def _coerce_plan_types(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce common type mismatches before validation."""
    if "estimated_word_count" in obj and isinstance(obj["estimated_word_count"], str):
        if obj["estimated_word_count"].isdigit():
            obj["estimated_word_count"] = int(obj["estimated_word_count"])
    for block in obj.get("content_blocks", []):
        if block.get("block_type") == "process_steps":
            for step in block.get("steps", []):
                if isinstance(step.get("step_number"), int):
                    step["step_number"] = str(step["step_number"])
    return obj


def validate_plan(data: str | dict):
    """Validate a plan JSON string or object."""
    try:
        if isinstance(data, str):
            obj = json.loads(data)
        else:
            obj = data
        obj = _coerce_plan_types(obj)
        return PlanModel.model_validate(obj)
    except ValidationError as e:
        details = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            msg = err["msg"]
            details.append(f"{loc}: {msg}")
        raise ValueError("; ".join(details))

