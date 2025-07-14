import json
import logging
from typing import Dict, Any

from showup_core.utils import load_prompt
from .block_library import get_block_type_definitions, validate_plan
from .planning_stage import repair_plan_json_with_llm
from simplified_workflow.template_builder import generate_markdown_template

logger = logging.getLogger(__name__)


async def run_refinement_stage(
    row_data_item: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Critique and refine an initial plan using either Anthropic or OpenAI models."""
    logger.info("Running refinement stage")

    new_item = row_data_item.copy()

    critique_path = config.get("critique_prompt_path") or "planning/plan_critique_prompt"
    refine_path = config.get("refine_prompt_path") or "planning/plan_refine_prompt"
    critique_template = load_prompt(critique_path)
    refine_template = load_prompt(refine_path)
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

    try:
        import openai
        from showup_core.api_client import get_openai_model_max_tokens

        client = openai.OpenAI(api_key=config.get('openai_api_key'))
        max_tokens = config.get('max_tokens', 1000)
        limit = get_openai_model_max_tokens(model_id)
        if max_tokens > limit:
            logger.debug(
                f"Reducing max_tokens from {max_tokens} to {limit} for model {model_id}"
            )
            max_tokens = limit

        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": critique_prompt}],
            max_tokens=max_tokens,
            temperature=config.get('temperature', 0.3)
        )
        critique = response.choices[0].message.content
        new_item["plan_critique"] = critique

        refine_prompt = refine_template.replace('{{learner_profile}}', learner_profile)
        refine_prompt = refine_prompt.replace('{{initial_plan}}', initial_plan_str)
        refine_prompt = refine_prompt.replace('{{critique}}', critique)
        refine_prompt = refine_prompt.replace('{{block_library}}', block_defs)

        response2 = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": refine_prompt}],
            max_tokens=max_tokens,
            temperature=config.get('temperature', 0.3)
        )
        revised_plan_text = response2.choices[0].message.content

        try:
            new_item["final_plan"] = validate_plan(revised_plan_text).model_dump(exclude_none=True)
        except Exception as val_err:
            logger.error(f"Refined plan validation failed: {val_err}")
            repaired = await repair_plan_json_with_llm(
                broken_text=revised_plan_text,
                api_key=config.get("openai_api_key"),
                model=model_id,
            )
            if repaired:
                new_item["final_plan"] = repaired.model_dump(exclude_none=True)
            else:
                raise

        try:
            template = await generate_markdown_template(new_item["final_plan"], config)
            new_item["markdown_template"] = template
        except Exception as templ_err:
            logger.error(f"Template generation failed: {templ_err}")
            new_item["markdown_template"] = ""

        new_item["status"] = "PLAN_FINALIZED"
    except Exception as e:
        logger.error(f"Refinement stage failed: {e}")
        new_item["status"] = "PLAN_FAILED"
        new_item["error"] = str(e)

    return new_item
