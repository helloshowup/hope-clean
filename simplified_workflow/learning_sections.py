import os
import logging
from typing import Tuple
from showup_core.api_client import generate_with_claude
from showup_core.utils import load_prompt

logger = logging.getLogger(__name__)


async def generate_lo_and_kt_from_content(content: str, model: str = 'claude-3-haiku-20240307', max_tokens: int = 800) -> Tuple[str, str]:
    """Generate learning objectives and key takeaways from lesson content."""
    prompt_template = load_prompt('generation/lo_kt_generation_prompt')
    if not prompt_template:
        logger.error('Prompt file not found')
        raise FileNotFoundError('lo_kt_generation_prompt missing')

    prompt = prompt_template.replace('{{content}}', content)
    response = await generate_with_claude(
        prompt=prompt,
        system_prompt=load_prompt('system/lo_kt_system_message'),
        max_tokens=max_tokens,
        temperature=0.3,
        model=model,
        task_type='learning_summaries'
    )
    return parse_lo_and_kt(response)

def parse_lo_and_kt(text: str) -> Tuple[str, str]:
    lo_marker = '## Learning Objectives'
    kt_marker = '## Key Takeaways'
    lo_start = text.find(lo_marker)
    kt_start = text.find(kt_marker)
    if lo_start == -1 or kt_start == -1:
        raise ValueError('Could not parse learning sections')
    lo_section = text[lo_start:kt_start].strip()
    kt_section = text[kt_start:].strip()
    return lo_section, kt_section
