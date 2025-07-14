import os
import json
import logging
from typing import Dict, Any

from showup_core.api_client import generate_with_claude
from showup_core.model_config import get_model_provider
from showup_core.utils import load_prompt
from .block_library import get_block_type_definitions, validate_plan

logger = logging.getLogger(__name__)


async def run_refinement_stage(
    row_data_item: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Critique and refine an initial plan using either Anthropic or OpenAI models."""
    logger.info("Running refinement stage")

    new_item = row_data_item.copy()

    critique_template = load_prompt(
        config.get("critique_prompt_path", "planning/plan_critique_prompt")
    )
    refine_template = load_prompt(
        config.get("refine_prompt_path", "planning/plan_refine_prompt")
    )
    if not critique_template or not refine_template:
        logger.error("Refinement prompts not found")
        new_item["status"] = "PLAN_FAILED"
        new_item["error"] = "Prompt not found"
        return new_item

    learner_profile = new_item.get("Learner Profile") or new_item.get(
        "learner_profile", ""
    )
    initial_plan_obj = new_item.get("initial_plan", {})
    initial_plan_str = json.dumps(initial_plan_obj, ensure_ascii=False)

    block_defs = get_block_type_definitions()

    critique_prompt = critique_template.replace('{{learner_profile}}', learner_profile)
    critique_prompt = critique_prompt.replace('{{initial_plan}}', initial_plan_str)
    critique_prompt = critique_prompt.replace('{{block_library}}', block_defs)

    model_id = config.get('model_id', 'claude-3-haiku-20240307')
    provider = get_model_provider(model_id)

    try:
        if provider == 'openai':
            import openai
            client = openai.OpenAI(api_key=config.get('openai_api_key'))
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": critique_prompt}],
                max_tokens=config.get('max_tokens', 1000),
                temperature=config.get('temperature', 0.3)
            )
            critique = response.choices[0].message.content
        else:
            critique = await generate_with_claude(
                critique_prompt,
                max_tokens=config.get('max_tokens', 1000),
                temperature=config.get('temperature', 0.3),
                model=model_id,
                task_type='plan_critique'
            )
        new_item["plan_critique"] = critique

        refine_prompt = refine_template.replace('{{learner_profile}}', learner_profile)
        refine_prompt = refine_prompt.replace('{{initial_plan}}', initial_plan_str)
        refine_prompt = refine_prompt.replace('{{critique}}', critique)
        refine_prompt = refine_prompt.replace('{{block_library}}', block_defs)

        if provider == 'openai':
            response2 = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": refine_prompt}],
                max_tokens=config.get('max_tokens', 1000),
                temperature=config.get('temperature', 0.3)
            )
            revised_plan_text = response2.choices[0].message.content
        else:
            revised_plan_text = await generate_with_claude(
                refine_prompt,
                max_tokens=config.get('max_tokens', 1000),
                temperature=config.get('temperature', 0.3),
                model=model_id,
                task_type='plan_refine'
            )

        new_item["final_plan"] = validate_plan(revised_plan_text).model_dump(exclude_none=True)
        new_item["status"] = "PLAN_FINALIZED"
    except Exception as e:
        logger.error(f"Refinement stage failed: {e}")
        new_item["status"] = "PLAN_FAILED"
        new_item["error"] = str(e)

    return new_item
