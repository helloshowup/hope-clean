import os
import json
import logging
import asyncio
from typing import Dict, Any

from .showup_core.api_client import generate_with_claude
from .showup_core.model_config import get_model_provider

logger = logging.getLogger(__name__)

PLANNING_PROMPT_PATH = os.path.join(os.path.dirname(__file__), 'prompts', 'planning_prompt.txt')

async def run_planning_stage(row_data_item: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a preliminary plan using either Anthropic or OpenAI models."""
    logger.info("Running planning stage")

    try:
        with open(PLANNING_PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error(f"Planning prompt not found: {PLANNING_PROMPT_PATH}")
        row_data_item['status'] = 'PLAN_FAILED'
        row_data_item['error'] = f"Prompt not found: {PLANNING_PROMPT_PATH}"
        return row_data_item

    content_outline = row_data_item.get('Content Outline') or row_data_item.get('content_outline', '')
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

        row_data_item['initial_plan'] = json.loads(ai_response)
        row_data_item['status'] = 'PLAN_GENERATED'
    except Exception as e:
        logger.error(f"Planning stage failed: {e}")
        row_data_item['status'] = 'PLAN_FAILED'
        row_data_item['error'] = str(e)

    return row_data_item
