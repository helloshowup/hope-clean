import os
import logging
import re
from typing import Tuple
from showup_core.api_client import generate_with_ai
from showup_core.utils import load_prompt
from showup_core.model_config import load_model_config

models_cfg = load_model_config()

logger = logging.getLogger(__name__)


async def generate_lo_and_kt_from_content(content: str, model: str = models_cfg["lo_kt_model"], max_tokens: int = 800) -> Tuple[str, str]:
    """Generate learning objectives and key takeaways from lesson content."""
    prompt_template = load_prompt('generation/lo_kt_generation_prompt')
    if not prompt_template:
        logger.error('Prompt file not found')
        raise FileNotFoundError('lo_kt_generation_prompt missing')

    prompt = prompt_template.replace('{{content}}', content)
    response = await generate_with_ai(
        prompt=prompt,
        system_prompt=load_prompt('system/lo_kt_system_message'),
        max_tokens=max_tokens,
        temperature=0.3,
        model=model,
        task_type='learning_summaries'
    )
    return parse_lo_and_kt(response)

def parse_lo_and_kt(text: str) -> Tuple[str, str]:
    """Parse learning objectives and key takeaways from AI response."""
    pattern = re.compile(
        r"##\s*Learning Objectives\s*(.*?)\s*##\s*Key Takeaways\s*(.*)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        logger.debug("Raw LO/KT response that failed to parse:\n%s", text)
        raise ValueError("Could not parse learning sections")

    lo_content = match.group(1).strip()
    kt_content = match.group(2).strip()
    lo_section = "## Learning Objectives\n" + lo_content
    kt_section = "## Key Takeaways\n" + kt_content
    return lo_section, kt_section
