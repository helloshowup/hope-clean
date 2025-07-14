import os
import logging
import asyncio
import json
from typing import Dict, Any

from showup_core.api_client import generate_with_claude, _load_selected_model
from showup_core.model_config import (
    get_model_provider,
    DEFAULT_PLANNING_MODEL,
)
from showup_core.utils import load_prompt
from .block_library import get_block_type_definitions, validate_plan

logger = logging.getLogger(__name__)


async def run_planning_stage(
    row_data_item: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a preliminary plan using either Anthropic or OpenAI models."""
    logger.info("Running planning stage")

    new_item = row_data_item.copy()

    prompt_path = config.get("planning_prompt_path") or "planning/main_lesson_planner"
    prompt_template = load_prompt(prompt_path)
    if not prompt_template:
        logger.error("Planning prompt not found")
        new_item["status"] = "PLAN_FAILED"
        new_item["error"] = "Prompt not found"
        return new_item

    content_outline = new_item.get("Content Outline") or new_item.get(
        "content_outline", ""
    )
    learner_profile = new_item.get("Learner Profile") or new_item.get(
        "learner_profile", ""
    )
    rationale = new_item.get("What is the rationale for this step") or new_item.get(
        "rationale", ""
    )
    # Strictly rely on the CSV value; don't fall back to defaults
    word_count = str(new_item.get("word_count", ""))
    block_defs = get_block_type_definitions()
    prompt = (
        prompt_template.replace("{{content_outline}}", content_outline)
        .replace("{{learner_profile}}", learner_profile)
        .replace("{{rationale}}", rationale)
        .replace("{{word_count}}", word_count)
        .replace("{{block_library}}", block_defs)
    )

    model_id = config.get('model_id', _load_selected_model(DEFAULT_PLANNING_MODEL))
    provider = get_model_provider(model_id)

    max_attempts = config.get("max_attempts", 3)
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            if provider == 'openai':
                import openai
                from showup_core.api_client import get_openai_model_max_tokens

                client = openai.OpenAI(api_key=config.get('openai_api_key'))

                max_tokens = config.get('max_tokens', 8000)
                limit = get_openai_model_max_tokens(model_id)
                if max_tokens > limit:
                    logger.debug(
                        f"Reducing max_tokens from {max_tokens} to {limit} for model {model_id}"
                    )
                    max_tokens = limit

                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=config.get('temperature', 0.3)
                )
                ai_response = response.choices[0].message.content
            else:
                ai_response = await generate_with_claude(
                    prompt,
                    max_tokens=config.get('max_tokens', 8000),
                    temperature=config.get('temperature', 0.3),
                    model=model_id,
                    task_type='planning'
                )

            new_item["initial_plan"] = validate_plan(ai_response).model_dump(exclude_none=True)
            new_item["status"] = "PLAN_GENERATED"
            break
        except Exception as e:
            last_error = e
            logger.error(f"Planning attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                await asyncio.sleep(1)

    if new_item.get("status") != "PLAN_GENERATED":
        new_item["status"] = "PLAN_FAILED"
        new_item["error"] = str(last_error) if last_error else "unknown error"

    return new_item
