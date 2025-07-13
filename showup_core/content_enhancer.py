"""
Content enhancement utilities for ShowupSquared.

This module provides utilities for enhancing, analyzing, and transforming
educational content, including quality assessment, summarization, and contextual enhancements. This file might be redundant and could possible be replaced by being absorbed logically into other modules
"""

import os
import re
import logging
import json
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("content_enhancer")

class QualityAnalyzer:
    """Analyzes content quality and provides enhancement recommendations."""
    
    def __init__(self):
        """Initialize the QualityAnalyzer."""
        self.logger = logging.getLogger("content_enhancer.quality")
    
    def analyze(self, content: str, content_type: str = "lesson") -> Dict[str, Any]:
        """
        Analyze content quality and provide recommendations.
        
        Args:
            content: Content to analyze
            content_type: Type of content (lesson, article, etc.)
            
        Returns:
            Dictionary with analysis results
        """
        # Basic metrics
        metrics = self._calculate_basic_metrics(content)
        
        # Content-specific analysis
        if content_type == "lesson":
            quality_score, issues = self._analyze_lesson_content(content, metrics)
        elif content_type == "article":
            quality_score, issues = self._analyze_article_content(content, metrics)
        else:
            quality_score, issues = self._analyze_generic_content(content, metrics)
        
        # Build result
        return {
            "metrics": metrics,
            "quality_score": quality_score,
            "issues": issues,
            "recommendations": self._generate_recommendations(issues)
        }
    
    def _calculate_basic_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate basic content metrics."""
        lines = content.split("\n")
        words = re.findall(r'\b\w+\b', content)
        
        metrics = {
            "char_count": len(content),
            "word_count": len(words),
            "line_count": len(lines),
            "paragraph_count": len([l for l in lines if l.strip()]),
            "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
            "heading_count": len(re.findall(r'^#+\s+', content, re.MULTILINE)),
            "code_block_count": len(re.findall(r'```', content)) // 2,
            "image_count": len(re.findall(r'!\[.*?\]\(.*?\)', content)),
        }
        
        return metrics
    
    def _analyze_lesson_content(self, content: str, metrics: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Analyze educational lesson content quality."""
        issues = []
        
        # Check for section structure (typical lesson sections)
        if not re.search(r'^#+\s+Introduction', content, re.MULTILINE | re.IGNORECASE):
            issues.append("Missing introduction section")
        
        if not re.search(r'^#+\s+Summary|Conclusion', content, re.MULTILINE | re.IGNORECASE):
            issues.append("Missing summary or conclusion section")
        
        # Check for learning objectives
        if not re.search(r'learning objectives|objectives|goals', content, re.MULTILINE | re.IGNORECASE):
            issues.append("No clear learning objectives found")
        
        # Check for educational elements
        if metrics["image_count"] < 1:
            issues.append("Consider adding visual elements (images, diagrams)")
        
        if metrics["heading_count"] < 3:
            issues.append("Content may need better section structure with more headings")
        
        # Calculate quality score - starting from 10 and subtracting for issues
        quality_score = 10.0 - (len(issues) * 0.5)
        
        # Ensure score is in 0-10 range
        quality_score = max(0, min(10, quality_score))
        
        return quality_score, issues
    
    def _analyze_article_content(self, content: str, metrics: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Analyze article content quality."""
        issues = []
        
        # Check for article structure
        if not re.search(r'^#+\s+', content, re.MULTILINE):
            issues.append("Missing title or main heading")
        
        # Check for paragraphs and flow
        if metrics["paragraph_count"] < 3:
            issues.append("Article has too few paragraphs")
        
        # Check for reader engagement
        if metrics["avg_word_length"] > 7:
            issues.append("Word choice may be too complex (high average word length)")
        
        # Check for visual interest
        if metrics["image_count"] < 1:
            issues.append("Consider adding images to enhance article")
        
        # Calculate quality score - starting from 10 and subtracting for issues
        quality_score = 10.0 - (len(issues) * 0.5)
        
        # Ensure score is in 0-10 range
        quality_score = max(0, min(10, quality_score))
        
        return quality_score, issues
    
    def _analyze_generic_content(self, content: str, metrics: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Analyze generic content quality."""
        issues = []
        
        # Check for basic structure
        if metrics["heading_count"] < 1:
            issues.append("Missing headings or structure")
        
        # Check for adequate content length
        if metrics["word_count"] < 100:
            issues.append("Content may be too short")
        
        # Check for content organization
        if metrics["paragraph_count"] < 2:
            issues.append("Text lacks paragraph structure")
        
        # Calculate quality score - starting from 10 and subtracting for issues
        quality_score = 10.0 - (len(issues) * 0.5)
        
        # Ensure score is in 0-10 range
        quality_score = max(0, min(10, quality_score))
        
        return quality_score, issues
    
    def _generate_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations based on identified issues."""
        recommendations = []
        
        for issue in issues:
            if "missing introduction" in issue.lower():
                recommendations.append("Add a clear introduction that sets the context for the content")
            
            elif "missing summary" in issue.lower():
                recommendations.append("Add a conclusion or summary to reinforce key takeaways")
            
            elif "learning objectives" in issue.lower():
                recommendations.append("Define clear learning objectives at the beginning of the content")
            
            elif "visual elements" in issue.lower() or "images" in issue.lower():
                recommendations.append("Enhance engagement by adding relevant images, diagrams, or visual aids")
            
            elif "section structure" in issue.lower() or "heading" in issue.lower():
                recommendations.append("Improve structure by adding more section headings and subheadings")
            
            elif "too few paragraphs" in issue.lower():
                recommendations.append("Break content into more paragraphs to improve readability")
            
            elif "word choice" in issue.lower():
                recommendations.append("Simplify language to improve clarity and readability")
            
            elif "too short" in issue.lower():
                recommendations.append("Expand content with more examples, explanations, or details")
            
            else:
                # Generic recommendation for other issues
                recommendations.append(f"Address the following issue: {issue}")
        
        return recommendations

class AIDetector:
    """Detects AI-generated content and provides remediation suggestions."""
    
    def __init__(self, sensitivity: str = "medium"):
        """
        Initialize the AIDetector.
        
        Args:
            sensitivity: Detection sensitivity ('low', 'medium', 'high')
        """
        self.logger = logging.getLogger("content_enhancer.ai_detector")
        self.sensitivity = sensitivity
        
        # Load AI phrases dataset if available
        self.ai_phrases = self._load_ai_phrases()
    
    def _load_ai_phrases(self) -> List[str]:
        """Load common AI phrases for detection."""
        phrases = []
        try:
            # Try to load from multiple potential locations
            locations = [
                os.path.join("data", "ai_phrases.json"),
                os.path.join("data", "config", "ai_phrases.json"),
                os.path.join("config", "ai_phrases.json")
            ]
            
            for loc in locations:
                if os.path.exists(loc):
                    with open(loc, 'r', encoding='utf-8') as f:
                        phrases = json.load(f)
                        self.logger.info(f"AI phrases file exists at {loc}")
                        break
        except Exception as e:
            self.logger.warning(f"Could not load AI phrases file: {str(e)}")
        
        return phrases
    
    def analyze(self, content: str) -> Dict[str, Any]:
        """
        Analyze content for AI indicators.
        
        Args:
            content: Content to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Calculate AI indicators
        indicators = self._find_ai_indicators(content)
        
        # Get threshold based on sensitivity
        threshold = {
            "low": 0.7,
            "medium": 0.5,
            "high": 0.3
        }.get(self.sensitivity, 0.5)
        
        # Calculate total score
        score = sum(i["weight"] for i in indicators)
        
        # Determine if content is likely AI-generated
        is_ai_generated = score >= threshold
        
        return {
            "is_ai_generated": is_ai_generated,
            "ai_score": min(1.0, score),  # Cap at 1.0
            "indicators": indicators,
            "remediation": self._generate_remediation_suggestions(indicators) if is_ai_generated else []
        }
    
    def _find_ai_indicators(self, content: str) -> List[Dict[str, Any]]:
        """Find indicators of AI-generated content."""
        indicators = []
        
        # Check for common AI phrases
        for phrase in self.ai_phrases:
            if phrase.lower() in content.lower():
                indicators.append({
                    "type": "ai_phrase",
                    "description": f"Common AI phrase: '{phrase}'",
                    "weight": 0.1
                })
        
        # Check for repetitive structures
        if self._has_repetitive_structure(content):
            indicators.append({
                "type": "repetitive_structure",
                "description": "Content has repetitive paragraph structures",
                "weight": 0.15
            })
        
        # Check for formulaic transitions
        formulaic_transitions = re.findall(r'\b(in conclusion|to summarize|in summary|firstly|secondly|thirdly|finally|moreover|furthermore)\b', 
                                         content, re.IGNORECASE)
        if len(formulaic_transitions) > 3:
            indicators.append({
                "type": "formulaic_transitions",
                "description": f"Found {len(formulaic_transitions)} formulaic transitions",
                "weight": 0.1
            })
        
        # Check for lack of personal voice/perspective
        first_person_count = len(re.findall(r'\b(I|my|mine|myself)\b', content, re.IGNORECASE))
        if first_person_count == 0 and len(content.split()) > 200:
            indicators.append({
                "type": "impersonal",
                "description": "Content lacks personal voice (no first-person perspective)",
                "weight": 0.1
            })
        
        # Check for perfect grammatical structure
        error_indicators = ['irregardless', 'their is', 'there are a', 'would of', 'could of']
        has_typical_errors = any(e in content.lower() for e in error_indicators)
        if not has_typical_errors and len(content.split()) > 300:
            indicators.append({
                "type": "perfect_grammar",
                "description": "Content has unusually perfect grammar and no typical human errors",
                "weight": 0.15
            })
        
        return indicators
    
    def _has_repetitive_structure(self, content: str) -> bool:
        """Check if content has repetitive paragraph structures."""
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        
        if len(paragraphs) < 4:
            return False
        
        # Check paragraph length pattern
        lengths = [len(p.split()) for p in paragraphs]
        length_variation = max(1, sum(lengths)) / max(1, len(lengths))
        
        # If paragraph lengths are too consistent, it's suspicious
        if length_variation < 20 and len(paragraphs) > 5:
            return True
        
        return False
    
    def _generate_remediation_suggestions(self, indicators: List[Dict[str, Any]]) -> List[str]:
        """Generate suggestions to make content less AI-detectable."""
        suggestions = []
        
        for indicator in indicators:
            if indicator["type"] == "ai_phrase":
                suggestions.append("Replace common AI phrases with more original language")
            
            elif indicator["type"] == "repetitive_structure":
                suggestions.append("Vary paragraph structure and length to make content flow more naturally")
            
            elif indicator["type"] == "formulaic_transitions":
                suggestions.append("Reduce use of formulaic transitions and use more natural connections between ideas")
            
            elif indicator["type"] == "impersonal":
                suggestions.append("Add personal perspective or experiences to make content more authentic")
            
            elif indicator["type"] == "perfect_grammar":
                suggestions.append("Make content feel more natural by varying sentence structure and complexity")
        
        # Add general suggestions
        if len(indicators) > 0:
            suggestions.append("Edit the content to include human perspective, experiences, or anecdotes")
            suggestions.append("Revise to use a more conversational and less formal tone")
        
        return suggestions

class ContentEnhancer:
    """Enhances educational content with improved structure, examples, and readability."""
    
    def __init__(self):
        """Initialize the ContentEnhancer."""
        self.logger = logging.getLogger("content_enhancer")
        self.quality_analyzer = QualityAnalyzer()
        self.ai_detector = AIDetector()
    
    def analyze_content_quality(self, content: str, content_type: str = "lesson") -> Dict[str, Any]:
        """
        Analyze content quality and provide enhancement recommendations.
        
        Args:
            content: Content to analyze
            content_type: Type of content (lesson, article, etc.)
            
        Returns:
            Dictionary with analysis results
        """
        # Analyze content quality
        quality_results = self.quality_analyzer.analyze(content, content_type)
        
        # Analyze for AI detection
        ai_results = self.ai_detector.analyze(content)
        
        # Combine results
        return {
            "quality": quality_results,
            "ai_detection": ai_results,
            "overall_score": (quality_results["quality_score"] * 0.7) + 
                            ((1 - ai_results["ai_score"]) * 3),  # Higher score when less AI-like
            "enhance_priority": len(quality_results["issues"]) > 1 or ai_results["is_ai_generated"]
        }
    
    def extract_context_element(self, content: str, element_type: str) -> str:
        """
        Extract a specific element from content.
        
        Args:
            content: Content to extract from
            element_type: Type of element to extract (title, introduction, summary, etc.)
            
        Returns:
            Extracted element or empty string if not found
        """
        if element_type == "title":
            # Extract title (first h1 heading)
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                return title_match.group(1).strip()
        
        elif element_type == "introduction":
            # Extract introduction (text after title until next heading)
            intro_match = re.search(r'^#\s+.+\n+(.+?)(?=\n+#{2,}|\Z)', content, re.MULTILINE | re.DOTALL)
            if intro_match:
                return intro_match.group(1).strip()
        
        elif element_type == "summary":
            # Extract summary/conclusion section
            summary_match = re.search(r'^##\s+(Summary|Conclusion)(.+?)(?=\n+#{2,}|\Z)', 
                                     content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            if summary_match:
                return summary_match.group(2).strip()
        
        elif element_type == "main_points":
            # Extract all h2 headings as main points
            main_points = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
            return "\n".join(f"- {point}" for point in main_points)
        
        elif element_type == "keywords":
            # Extract words that appear to be keywords (emphasized or in headings)
            # First, find emphasized text
            emphasized = re.findall(r'\*\*(.+?)\*\*', content)
            
            # Then find heading text
            headings = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
            
            # Extract potential keywords by splitting and cleaning
            all_words = []
            for text in emphasized + headings:
                all_words.extend(re.findall(r'\b[A-Za-z]{4,}\b', text))
            
            # Count frequency
            from collections import Counter
            word_counts = Counter(w.lower() for w in all_words)
            
            # Take top keywords
            keywords = [word for word, count in word_counts.most_common(10)]
            return ", ".join(keywords)
        
        # If no match or unsupported element_type
        return ""
    
    def summarize_content(self, content: str, max_length: int = 200) -> str:
        """
        Create a summary of content.
        
        Args:
            content: Content to summarize
            max_length: Maximum length in words
            
        Returns:
            Summarized content
        """
        # Extract title
        title = self.extract_context_element(content, "title")
        
        # Extract introduction and summary if available
        intro = self.extract_context_element(content, "introduction")
        existing_summary = self.extract_context_element(content, "summary")
        
        # Extract main points
        main_points = self.extract_context_element(content, "main_points")
        
        # Combine elements for summary
        summary_parts = []
        
        if title:
            summary_parts.append(f"# {title} - Summary")
        
        if intro and len(intro.split()) <= max_length // 2:
            summary_parts.append(intro)
        else:
            # Extract first sentence of intro
            intro_sentence = re.search(r'^(.+?[.!?])(?:\s|$)', intro)
            if intro_sentence:
                summary_parts.append(intro_sentence.group(1))
        
        if main_points:
            summary_parts.append("\n## Key Points\n" + main_points)
        
        if existing_summary:
            # If we have an existing summary and haven't exceeded max length
            current_length = sum(len(part.split()) for part in summary_parts)
            if current_length + len(existing_summary.split()) <= max_length:
                summary_parts.append("\n## Summary\n" + existing_summary)
        
        # Combine parts
        result = "\n\n".join(summary_parts)
        
        # Truncate if still too long
        words = result.split()
        if len(words) > max_length:
            result = " ".join(words[:max_length]) + "..."
        
        return result
    
    def enhance_content_section(self, content: str, section_type: str) -> str:
        """
        Enhance a specific section of content.
        
        Args:
            content: Section content to enhance
            section_type: Type of section (introduction, conclusion, example, etc.)
            
        Returns:
            Enhanced section content
        """
        # Basic enhancements for all section types
        enhanced = content
        
        # Remove redundant phrases
        redundant_phrases = [
            "as you can see", "as we can see", "it goes without saying",
            "needless to say", "it should be noted that", "it is important to note that"
        ]
        
        for phrase in redundant_phrases:
            enhanced = re.sub(r'\b' + re.escape(phrase) + r'\b', '', enhanced, flags=re.IGNORECASE)
        
        # Apply section-specific enhancements
        if section_type == "introduction":
            # Ensure introduction has a hook and sets up the content
            if not re.search(r'\?|!', enhanced[:200]):
                # No question or exclamation in first 200 chars, might need a hook
                enhanced = "**Why is this topic important?** " + enhanced
            
            # Ensure introduction describes what's coming
            if not re.search(r'will (learn|explore|discover|find|cover)', enhanced, re.IGNORECASE):
                enhanced += "\n\nIn this lesson, you'll learn key concepts and practical applications of this topic."
        
        elif section_type == "conclusion":
            # Ensure conclusion summarizes key points
            if not re.search(r'(summary|recap|review|key (point|concept|takeaway))', enhanced, re.IGNORECASE):
                enhanced = "**Key takeaways:** " + enhanced
            
            # Add forward-looking statement if missing
            if not re.search(r'(next|future|continue|further|advance)', enhanced, re.IGNORECASE):
                enhanced += "\n\nIn the next lesson, you'll build on these concepts and explore more advanced techniques."
        
        elif section_type == "example":
            # Format example clearly
            if not enhanced.startswith("**Example"):
                enhanced = "**Example:**\n\n" + enhanced
            
            # Add explanation of example if missing
            if not re.search(r'(demonstrates|shows|illustrates|exemplifies)', enhanced, re.IGNORECASE):
                enhanced += "\n\nThis example demonstrates how to apply the concepts in a real-world scenario."
        
        return enhanced.strip()
    
    def build_context_from_course_content(self, course_id: str, module_num: int, 
                                       lesson_num: Optional[int] = None,
                                       content_type: str = "module") -> Dict[str, str]:
        """
        Build context information from existing course content.
        
        Args:
            course_id: Course identifier
            module_num: Module number
            lesson_num: Optional lesson number
            content_type: Type of content to build context for
            
        Returns:
            Dictionary of context elements
        """
        # Import here to avoid circular imports
        from .config import get_course_content_paths, AVAILABLE_COURSES
        
        context = {}
        
        # Add course information
        if course_id in AVAILABLE_COURSES:
            context["course_name"] = AVAILABLE_COURSES[course_id]["name"]
            context["course_client"] = AVAILABLE_COURSES[course_id]["client"]
            context["course_level"] = AVAILABLE_COURSES[course_id]["level"]
        
        # Get content paths
        paths = get_course_content_paths(course_id, module_num, lesson_num)
        
        # Build context based on content type
        if content_type == "module":
            # Check if module content exists
            if os.path.exists(paths["module_path"]):
                with open(paths["module_path"], "r", encoding="utf-8") as f:
                    module_content = f.read()
                
                # Extract module information
                context["module_title"] = self.extract_context_element(module_content, "title")
                context["module_introduction"] = self.extract_context_element(module_content, "introduction")
                context["module_summary"] = self.extract_context_element(module_content, "summary")
                context["module_keywords"] = self.extract_context_element(module_content, "keywords")
        
        elif content_type == "lesson" and lesson_num is not None:
            # Check if module content exists for context
            if os.path.exists(paths["module_path"]):
                with open(paths["module_path"], "r", encoding="utf-8") as f:
                    module_content = f.read()
                
                # Extract module information for context
                context["module_title"] = self.extract_context_element(module_content, "title")
            
            # Check if lesson content exists
            if os.path.exists(paths["lesson_path"]):
                with open(paths["lesson_path"], "r", encoding="utf-8") as f:
                    lesson_content = f.read()
                
                # Extract lesson information
                context["lesson_title"] = self.extract_context_element(lesson_content, "title")
                context["lesson_introduction"] = self.extract_context_element(lesson_content, "introduction")
                context["lesson_summary"] = self.extract_context_element(lesson_content, "summary")
                context["lesson_keywords"] = self.extract_context_element(lesson_content, "keywords")
        
        return context

# Export standalone functions that wrap the class methods for easier use

def extract_context_element(content: str, element_type: str) -> str:
    """Extract a specific element from content."""
    enhancer = ContentEnhancer()
    return enhancer.extract_context_element(content, element_type)

def summarize_content(content: str, max_length: int = 200) -> str:
    """Create a summary of content."""
    enhancer = ContentEnhancer()
    return enhancer.summarize_content(content, max_length)

def enhance_content_section(content: str, section_type: str) -> str:
    """Enhance a specific section of content."""
    enhancer = ContentEnhancer()
    return enhancer.enhance_content_section(content, section_type)

def build_context_from_course_content(course_id: str, module_num: int, 
                                    lesson_num: Optional[int] = None,
                                    content_type: str = "module") -> Dict[str, str]:
    """Build context information from existing course content."""
    enhancer = ContentEnhancer()
    return enhancer.build_context_from_course_content(course_id, module_num, lesson_num, content_type)

def analyze_content_quality(content: str, content_type: str = "lesson") -> Dict[str, Any]:
    """Analyze content quality and provide enhancement recommendations."""
    enhancer = ContentEnhancer()
    return enhancer.analyze_content_quality(content, content_type)