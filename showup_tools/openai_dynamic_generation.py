import logging
import instructor
from openai import AsyncOpenAI
from .models import DynamicContentGenerationResult


log = logging.getLogger(__name__)


def get_instructor_client(api_key: str) -> AsyncOpenAI:
    """Create an OpenAI client patched with instructor for schema enforcement."""
    return instructor.from_openai(AsyncOpenAI(api_key=api_key))


async def repair_generated_json_with_llm(
    broken_text: str,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> DynamicContentGenerationResult | None:
    """Attempt to repair invalid JSON using the LLM itself."""
    log.info("Attempting to repair generated content JSON with LLM")
    client = get_instructor_client(api_key)
    try:
        return await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "The following text is malformed JSON that was supposed to conform to the DynamicContentGenerationResult schema. "
                        "Fix the JSON so it strictly conforms to the schema. Do not add any conversational text, just the corrected JSON."
                    ),
                },
                {"role": "user", "content": broken_text},
            ],
            temperature=0.0,
            response_model=DynamicContentGenerationResult,
        )
    except Exception as exc:
        log.error(f"Repair attempt for generated content failed: {exc}")
        return None


async def generate_structured_content(
    generation_prompt_text: str,
    api_key: str,
    model: str = "gpt-4o-mini",
    raw_llm_output_snippet: str | None = None,
) -> DynamicContentGenerationResult | None:
    """Generate structured dynamic content with schema enforcement and fallback."""
    client = get_instructor_client(api_key)
    try:
        generated_content_result = await client.chat.completions.create(
            model=model,
            response_model=DynamicContentGenerationResult,
            max_retries=2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate content structured into dynamic blocks based on the user's request. "
                        "Ensure the output strictly conforms to the DynamicContentGenerationResult JSON schema, "
                        "including all required fields for blocks and overall document structure."
                    ),
                },
                {"role": "user", "content": generation_prompt_text},
            ],
        )
        return generated_content_result
    except Exception as exc:
        log.error(f"Content generation API error during evaluation: {exc}")
        if raw_llm_output_snippet:
            repaired_result = await repair_generated_json_with_llm(
                broken_text=raw_llm_output_snippet,
                api_key=api_key,
                model=model,
            )
            if repaired_result:
                log.info("Successfully repaired generated content JSON using LLM fallback.")
            return repaired_result
        return None
