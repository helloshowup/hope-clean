from __future__ import annotations

from typing import List, Literal, Dict, Any, Optional
from pydantic import BaseModel, Field

class SentimentAnalysis(BaseModel):
    """Detailed sentiment analysis of text."""

    overall_sentiment: Literal["Positive", "Negative", "Neutral"] = Field(
        ..., description="The overall sentiment of the text."
    )
    score: float = Field(
        ..., description="A sentiment score from -1.0 (very negative) to 1.0 (very positive)."
    )

class DetectedAIPattern(BaseModel):
    """Represents a detected AI pattern category and its matches."""

    category: str = Field(
        ..., description="The category of the detected AI pattern (e.g., 'Comparisons')."
    )
    matches: List[str] = Field(
        default_factory=list, description="List of specific text snippets that matched the pattern."
    )

class DetectedAIPhrase(BaseModel):
    """Represents a specific AI phrase detected in the content."""

    phrase: str = Field(..., description="The specific AI phrase detected.")
    count: int = Field(..., description="Number of times this phrase was detected.")

class TextSegmentAnalysis(BaseModel):
    """Consolidated analysis results for a text segment."""

    sentiment: SentimentAnalysis = Field(..., description="Sentiment analysis for this segment.")
    detected_phrases: List[DetectedAIPhrase] = Field(
        default_factory=list,
        description="AI phrases detected in this segment, referencing 'ai_phrases.json'.",
    )
    detected_patterns: List[DetectedAIPattern] = Field(
        default_factory=list,
        description="AI pattern categories detected in this segment, referencing 'ai_patterns.json'.",
    )

class GeneratedContentBlock(BaseModel):
    """Represents a single dynamic content block within the generated output."""

    block_id: str = Field(..., description="A unique identifier for this content block.")
    block_type: str = Field(..., description="Type of content block (e.g., 'introduction').")
    title: Optional[str] = Field(None, description="Optional title for the content block.")
    content: str = Field(..., description="Actual text content of this block.")
    order: int = Field(..., description="Sequential order of this block within the document.")
    analysis: Optional[TextSegmentAnalysis] = Field(
        None, description="Optional analysis results specifically for this content block."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata specific to this block (e.g., source, generation parameters).",
    )

class DynamicContentGenerationResult(BaseModel):
    """Structured output from the dynamic block template generation phase."""

    document_id: str = Field(..., description="Unique identifier for the entire generated document.")
    document_title: str = Field(..., description="Overall title of the generated document.")
    generated_blocks: List[GeneratedContentBlock] = Field(
        ..., description="List of dynamically generated content blocks in order."
    )
    overall_summary: str = Field(
        ..., description="Concise one-paragraph summary of the entire generated document."
    )
    overall_sentiment: Optional[SentimentAnalysis] = Field(
        None, description="Optional overall sentiment analysis for the entire document."
    )
    generation_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata about the entire generation process."
    )
