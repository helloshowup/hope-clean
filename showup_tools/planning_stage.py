import os
import json
import logging
import asyncio
from typing import Dict, Any

from .showup_core.api_client import generate_with_claude
from .showup_core.model_config import get_model_provider

logger = logging.getLogger(__name__)

PLANNING_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "prompts", "planning_prompt.txt"
)

async def run_planning_stage(
    row_data_item: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a preliminary plan using either Anthropic or OpenAI models."""
    logger.info("Running planning stage")

    new_item = row_data_item.copy()

    prompt_path = config.get("planning_prompt_path", PLANNING_PROMPT_PATH)

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
    prompt = prompt_template.replace('{{content_outline}}', content_outline)

    model_id = config.get('model_id', 'claude-3-haiku-20240307')
    provider = get_model_provider(model_id)

    try:
        if provider == 'openai':
            import openai
            client = openai.OpenAI(api_key=config.get('openai_api_key'))
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.get('max_tokens', 1000),
                temperature=config.get('temperature', 0.3)
            )
            ai_response = response.choices[0].message.content
        else:
            ai_response = await generate_with_claude(
                prompt,
                max_tokens=config.get('max_tokens', 1000),
                temperature=config.get('temperature', 0.3),
                model=model_id,
                task_type='planning'
            )

        new_item["initial_plan"] = json.loads(ai_response)
        new_item["status"] = "PLAN_GENERATED"
    except Exception as e:
        logger.error(f"Planning stage failed: {e}")
        new_item["status"] = "PLAN_FAILED"
        new_item["error"] = str(e)

    return new_item
