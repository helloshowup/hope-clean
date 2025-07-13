#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Token counter for Claude models.

Provides accurate token counting for Claude API calls.
"""

import logging

# Configure logging
logger = logging.getLogger(__name__)

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not installed. Falling back to character-based approximation")


class ClaudeTokenizer:
    """Accurate token counter for Claude models with calibration"""
    
    def __init__(self):
        """Initialize the tokenizer with the best available method"""
        # Default calibration factor
        self.calibration_factor = 1.1  # Claude tends to count slightly more tokens than cl100k_base
        
        # Use tiktoken if available (more accurate than char counting)
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                self._calibrate()
                logger.info("Using tiktoken with calibration factor %.2f", self.calibration_factor)
            except Exception as e:
                logger.exception("Error initializing tiktoken: %s", e)
                self.tokenizer = None
        else:
            self.tokenizer = None
    
    def _calibrate(self):
        """Calibrate tiktoken counts against known Claude samples"""
        # Sample texts with approximate known Claude token counts
        # These are just estimates - ideally you'd have real Claude token counts
        samples = [
            ("This is a sample text to calibrate tokenization.", 10),
            ("The quick brown fox jumps over the lazy dog.", 10),
            ("Excel High School provides flexible, accredited, and student-centered education.", 14),
            ("Students are expected to maintain academic integrity and follow all policies.", 13)
        ]
        
        # Calculate calibration factor
        ratios = []
        for text, claude_count in samples:
            tiktoken_count = len(self.tokenizer.encode(text))
            if tiktoken_count > 0:  # Avoid division by zero
                ratios.append(claude_count / tiktoken_count)
        
        # Use the average ratio, but limit to reasonable bounds
        if ratios:
            avg_ratio = sum(ratios) / len(ratios)
            # Keep calibration within reasonable bounds
            self.calibration_factor = max(0.9, min(1.3, avg_ratio))
    
    def count_tokens(self, text: str) -> int:
        """Count tokens with the best available method
        
        Args:
            text: Text to count tokens in
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
            
        if self.tokenizer:
            # Apply calibration factor to tiktoken count
            return int(len(self.tokenizer.encode(text)) * self.calibration_factor)
        else:
            # Character-based approximation for Claude
            # Claude documentation suggests ~4-5 characters per token for English
            char_count = len(text)
            # Use 4.5 as a middle ground for characters per token
            return int(char_count / 4.5)


# Create a singleton instance for easy import
tokenizer = ClaudeTokenizer()


def count_tokens(text: str) -> int:
    """Convenience function to count tokens in text
    
    Args:
        text: Text to count tokens in
        
    Returns:
        Estimated token count
    """
    return tokenizer.count_tokens(text)


if __name__ == "__main__":
    # Simple self-test
    test_strings = [
        "This is a short test string.",
        "This is a slightly longer test string with more words and characters to analyze.",
        "Excel High School provides flexible, accredited online education for students worldwide."
    ]
    
    for s in test_strings:
        token_count = count_tokens(s)
        print(f"String: {s}\nLength: {len(s)} chars, Estimated tokens: {token_count}\n")
