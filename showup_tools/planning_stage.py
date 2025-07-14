import os
import logging
import asyncio
import json
from typing import Dict, Any

from showup_core.api_client import generate_with_claude
from showup_core.model_config import (
    get_model_provider,
    DEFAULT_PLANNING_MODEL,
)
from .block_library import get_block_type_definitions, validate_plan

logger = logging.getLogger(__name__)

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
PLANNING_PROMPT_PATH = os.path.join(PROMPTS_DIR, "planning_prompt.txt")

async def run_planning_stage(
    row_data_item: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a preliminary plan using either Anthropic or OpenAI models."""
    logger.info("Running planning stage")

    new_item = row_data_item.copy()

    prompt_path = config.get("planning_prompt_path") or PLANNING_PROMPT_PATH

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error(f"Planning prompt not found: {prompt_path}")
        new_item["status"] = "PLAN_FAILED"
        new_item["error"] = f"Prompt not found: {prompt_path}"
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
    word_count = str(
        new_item.get("word_count")
        or config.get("word_count")
        or ""
    )
    block_defs = get_block_type_definitions()
    prompt = (
        prompt_template.replace("{{content_outline}}", content_outline)
        .replace("{{learner_profile}}", learner_profile)
        .replace("{{rationale}}", rationale)
        .replace("{{word_count}}", word_count)
        .replace("{{block_library}}", block_defs)
    )

    model_id = config.get('model_id', DEFAULT_PLANNING_MODEL)
    provider = get_model_provider(model_id)

    max_attempts = config.get("max_attempts", 3)
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            if provider == 'openai':
                import openai
                client = openai.OpenAI(api_key=config.get('openai_api_key'))
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=config.get('max_tokens', 8000),
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
