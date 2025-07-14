import unittest
from showup_tools.models import (
    SentimentAnalysis,
    DetectedAIPattern,
    DetectedAIPhrase,
    TextSegmentAnalysis,
    GeneratedContentBlock,
    DynamicContentGenerationResult,
)

class TestGenerationOutputModels(unittest.TestCase):
    def test_dynamic_result_parsing(self):
        sample = {
            "document_id": "doc1",
            "document_title": "Sample Document",
            "generated_blocks": [
                {
                    "block_id": "b1",
                    "block_type": "introduction",
                    "title": "Intro",
                    "content": "Hello world",
                    "order": 1,
                    "metadata": {"foo": "bar"}
                }
            ],
            "overall_summary": "Summary text",
            "generation_metadata": {"model": "test"}
        }

        result = DynamicContentGenerationResult.model_validate(sample)
        self.assertEqual(result.document_id, "doc1")
        self.assertEqual(result.generated_blocks[0].block_type, "introduction")

if __name__ == '__main__':
    unittest.main()
