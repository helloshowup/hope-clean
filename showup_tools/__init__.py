# Initialize the simplified_app package
from .planning_stage import run_planning_stage
from .refinement_stage import run_refinement_stage
from .models import (
    SentimentAnalysis,
    DetectedAIPattern,
    DetectedAIPhrase,
    TextSegmentAnalysis,
    GeneratedContentBlock,
    DynamicContentGenerationResult,
)
from .openai_dynamic_generation import (
    generate_structured_content,
    repair_generated_json_with_llm,
)

__all__ = [
    'run_planning_stage',
    'run_refinement_stage',
    'SentimentAnalysis',
    'DetectedAIPattern',
    'DetectedAIPhrase',
    'TextSegmentAnalysis',
    'GeneratedContentBlock',
    'DynamicContentGenerationResult',
    'generate_structured_content',
    'repair_generated_json_with_llm',
]
