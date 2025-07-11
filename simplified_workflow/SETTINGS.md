# Settings Configuration for Simplified Workflow

This document explains the settings that can be configured for the simplified workflow.

## Settings File Format

The settings file should be a JSON file with the following structure:

```json
{
  "generation_settings": {
    "temperature": 0.5,
    "max_tokens": 4000,
    "word_count": 800,
    "model": "claude-3-opus-20240229"
  },
  "output_settings": {
    "base_output_dir": "output",
    "include_metadata": true,
    "save_intermediate_results": true
  },
  "workflow_settings": {
    "enable_image_placeholders": true,
    "detection_sensitivity": "medium",
    "save_workflow_log": true
  },
  "ui_settings": {
    "theme": "light",
    "language": "en",
    "show_advanced_options": false
  },
  "template_settings": {
    "article": {
      "word_count": 800,
      "max_tokens": 4000
    },
    "video": {
      "word_count": 300,
      "max_tokens": 2000
    }
  }
}
```

## Settings Explanation

### Generation Settings

These settings control how content is generated using the Claude API:

- `temperature`: Controls the randomness of the generated content. Lower values (e.g., 0.3) make the output more deterministic, while higher values (e.g., 0.7) make it more creative. Default: 0.5
- `max_tokens`: Maximum number of tokens to generate. Default: 4000
- `word_count`: Target word count for the generated content. This is similar to asking Claude to "write a 500-word essay". Default: 500
- `model`: The Claude model to use. Options include "claude-3-opus-20240229", "claude-3-sonnet-20240229", or "claude-3-haiku-20240307". Default: "claude-3-opus-20240229"

### Output Settings

These settings control how the output is saved:

- `base_output_dir`: Base directory for output files. Default: "output"
- `include_metadata`: Whether to include metadata in the output files. Default: true
- `save_intermediate_results`: Whether to save intermediate results (e.g., before AI detection). Default: true

### Workflow Settings

These settings control the workflow behavior:

- `enable_image_placeholders`: Whether to enable image placeholder suggestions in the content. Default: true
- `detection_sensitivity`: Sensitivity level for AI detection. Options are "low", "medium", or "high". Default: "medium"
- `save_workflow_log`: Whether to save a detailed workflow log. Default: true

### UI Settings

These settings control the UI appearance and behavior:

- `theme`: UI theme. Options are "light" or "dark". Default: "light"
- `language`: UI language. Default: "en"
- `show_advanced_options`: Whether to show advanced options in the UI. Default: false

### Template Settings

These settings allow you to configure different word counts and token limits for different template types:

- Each key in the `template_settings` object should match the "Template Type" column in your CSV file
- For each template type, you can specify:
  - `word_count`: Target word count for this specific template type
  - `max_tokens`: Maximum tokens for this specific template type
  - `temperature`: Temperature setting for this specific template type
  - `model`: Model to use for this specific template type

This allows you to have different word counts for different types of content (e.g., longer articles, shorter video scripts).

## Default Settings

If no settings file is provided, the workflow will use default values for all settings. The default values are the same as shown in the example above.

## Settings Usage

The settings are used in various parts of the workflow:

1. **Generation Settings**: Used when calling the Claude API to generate content.
2. **Output Settings**: Used when saving the generated content to files.
3. **Workflow Settings**: Used to control the behavior of the workflow, such as AI detection sensitivity.
4. **UI Settings**: Used to control the appearance and behavior of the UI.
5. **Template Settings**: Used to specify different word counts and token limits for different template types.

## Example Settings File

A sample settings file is provided in `test_data/sample_settings.json`. You can use this as a starting point for your own settings file.

## Notes

- All settings are optional. If a setting is not provided, the default value will be used.
- The settings file is passed to the workflow as a whole, and each component extracts the settings it needs.
- Some settings may not be fully implemented in the current version of the workflow.