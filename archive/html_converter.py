"""
HTML conversion utilities for ShowupSquared.

This module provides utilities for converting Markdown content to HTML
and enhancing HTML content with metadata, images, and styling.
"""

import os
import re
import logging
import markdown
from typing import Dict, Any, Optional

logger = logging.getLogger("html_converter")

def process_html_metadata(html_content: str, metadata: Dict[str, Any]) -> str:
    """
    Process and inject metadata into HTML content.
    
    Args:
        html_content: HTML content to process
        metadata: Dictionary of metadata to inject
        
    Returns:
        HTML content with metadata
    """
    # Create metadata block
    meta_html = "<div class='metadata' style='display:none;'>\n"
    for key, value in metadata.items():
        meta_html += f"  <meta name='{key}' content='{value}'>\n"
    meta_html += "</div>\n"
    
    # Inject after opening body tag or at the beginning
    if "<body" in html_content:
        html_content = re.sub(r"(<body[^>]*>)", r"\1\n" + meta_html, html_content)
    else:
        html_content = meta_html + html_content
        
    return html_content

def create_html_base(title: str, css: Optional[str] = None) -> str:
    """
    Create a base HTML document with standard structure.
    
    Args:
        title: Page title
        css: Optional CSS to include
        
    Returns:
        Base HTML document
    """
    # Set default CSS if none provided
    if css is None:
        css = """
        body { 
            font-family: Arial, sans-serif; 
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }
        h1, h2, h3, h4, h5, h6 { 
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            color: #333;
        }
        h1 { font-size: 2em; }
        h2 { font-size: 1.5em; }
        h3 { font-size: 1.2em; }
        p { margin-bottom: 1em; }
        img { 
            max-width: 100%; 
            height: auto;
            display: block;
            margin: 1em auto;
        }
        pre {
            background-color: #f5f5f5;
            padding: 1em;
            border-radius: 5px;
            overflow-x: auto;
        }
        code {
            background-color: #f5f5f5;
            padding: 0.2em 0.4em;
            border-radius: 3px;
        }
        blockquote {
            border-left: 4px solid #ddd;
            padding-left: 1em;
            color: #666;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        .image-placeholder {
            background-color: #eee;
            border: 1px dashed #aaa;
            padding: 20px;
            text-align: center;
            margin: 1em 0;
            color: #666;
        }
        """
    
    # Create HTML document
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css}
    </style>
</head>
<body>
    <div class="content">
        <!-- Content will be inserted here -->
    </div>
</body>
</html>
"""
    
    return html

def process_html_section(html_content: str, 
                       section_id: str, 
                       title: Optional[str] = None, 
                       class_name: Optional[str] = None) -> str:
    """
    Wrap HTML content in a section with optional title.
    
    Args:
        html_content: HTML content to wrap
        section_id: ID for the section
        title: Optional title for the section
        class_name: Optional CSS class for the section
        
    Returns:
        HTML content wrapped in a section
    """
    # Clean ID (remove spaces, etc.)
    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '-', section_id)
    
    # Create section opening tag
    section_html = f"<section id='{clean_id}'"
    if class_name:
        section_html += f" class='{class_name}'"
    section_html += ">\n"
    
    # Add title if provided
    if title:
        section_html += f"<h2>{title}</h2>\n"
    
    # Add content and close section
    section_html += html_content + "\n</section>\n"
    
    return section_html

def convert_markdown_to_html(markdown_content: str, 
                          module_number: Optional[int] = None,
                          lesson_number: Optional[int] = None,
                          use_standardized_images: bool = True, 
                          include_audio: bool = False) -> str:
    """
    Convert Markdown content to HTML with appropriate styling.
    
    Args:
        markdown_content: Markdown content to convert
        module_number: Optional module number for metadata
        lesson_number: Optional lesson number for metadata
        use_standardized_images: Whether to use standardized image paths
        include_audio: Whether to include audio elements
        
    Returns:
        HTML content
    """
    # Extract title from markdown (first h1)
    title_match = re.search(r'^# (.*?)$', markdown_content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Converted Content"
    
    # Create base HTML
    html_base = create_html_base(title)
    
    # Process image paths if using standardized images
    if use_standardized_images:
        # Replace image references with standardized paths
        markdown_content = re.sub(
            r'!\[(.*?)\]\((.*?)\)', 
            lambda m: f'![{m.group(1)}](images/{os.path.basename(m.group(2))})',
            markdown_content
        )
    
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'nl2br'])
    html_content = md.convert(markdown_content)
    
    # Add image placeholders if requested
    if use_standardized_images:
        # Replace image tags with placeholders
        html_content = re.sub(
            r'<img src="images/(.*?)" alt="(.*?)"[^>]*>',
            r'<div class="image-placeholder">'
            r'<p>Image Placeholder: \2</p>'
            r'<p><em>Filename: \1</em></p>'
            r'</div>',
            html_content
        )
    
    # Add audio elements if requested
    if include_audio:
        # Add audio player after each section
        sections = re.split(r'<h[1-3]>', html_content)
        if len(sections) > 1:
            html_content = sections[0]
            for i, section in enumerate(sections[1:], 1):
                html_content += f"<h{min(i, 3)}>" + section
                html_content += f"""
                <div class="audio-player">
                    <p><em>Audio narration for this section</em></p>
                    <audio controls>
                        <source src="audio/section_{i}.mp3" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                </div>
                """
    
    # Create metadata
    metadata = {
        "generator": "ShowupSquared",
        "version": "1.0.0"
    }
    
    if module_number is not None:
        metadata["module"] = str(module_number)
    
    if lesson_number is not None:
        metadata["lesson"] = str(lesson_number)
    
    # Process metadata
    html_content = process_html_metadata(html_content, metadata)
    
    # Insert content into base
    html = html_base.replace("<!-- Content will be inserted here -->", html_content)
    
    return html

def convert_lesson_to_html(lesson_content: str, 
                        title: str,
                        use_standardized_images: bool = True,
                        include_audio: bool = False) -> str:
    """
    Convert a complete lesson to HTML.
    
    Args:
        lesson_content: Markdown content of the lesson
        title: Lesson title
        use_standardized_images: Whether to use standardized images
        include_audio: Whether to include audio elements
        
    Returns:
        Complete HTML for the lesson
    """
    # Extract lesson number from title if possible
    lesson_number = None
    module_number = None
    
    match = re.search(r'Module (\d+)[^\d]+Lesson (\d+)', title)
    if match:
        module_number = int(match.group(1))
        lesson_number = int(match.group(2))
    
    # Convert to HTML
    html = convert_markdown_to_html(
        lesson_content,
        module_number=module_number,
        lesson_number=lesson_number,
        use_standardized_images=use_standardized_images,
        include_audio=include_audio
    )
    
    return html

def convert_module_to_html(module_content: Dict[str, Any], 
                         module_number: int,
                         use_standardized_images: bool = True,
                         include_audio: bool = False) -> Dict[str, str]:
    """
    Convert a complete module with lessons to HTML.
    
    Args:
        module_content: Dictionary containing module content
        module_number: Module number
        use_standardized_images: Whether to use standardized images
        include_audio: Whether to include audio elements
        
    Returns:
        Dictionary of HTML content for module and each lesson
    """
    result = {}
    
    # Convert module overview
    if "overview_content" in module_content:
        overview_html = convert_markdown_to_html(
            module_content["overview_content"],
            module_number=module_number,
            use_standardized_images=use_standardized_images,
            include_audio=include_audio
        )
        result["overview"] = overview_html
    
    # Convert each lesson
    if "lessons" in module_content:
        for lesson_num, lesson_data in module_content["lessons"].items():
            if "content" in lesson_data:
                lesson_title = f"Module {module_number} - Lesson {lesson_num}"
                lesson_html = convert_lesson_to_html(
                    lesson_data["content"],
                    title=lesson_title,
                    use_standardized_images=use_standardized_images,
                    include_audio=include_audio
                )
                result[f"lesson_{lesson_num}"] = lesson_html
    
    return result

def generate_content_html(content: str, 
                       content_type: str, 
                       title: str,
                       use_standardized_images: bool = True) -> str:
    """
    Generate HTML content with appropriate formatting for different content types.
    
    Args:
        content: Markdown content to convert
        content_type: Type of content (article, video, quiz, etc.)
        title: Content title
        use_standardized_images: Whether to use standardized images
        
    Returns:
        HTML content formatted for the specified content type
    """
    # Process based on content type
    if content_type.lower() == "video":
        # Add video player section
        content = f"""# {title}

## Video

<div class="video-container">
    <iframe src="about:blank" data-src="video/placeholder.mp4" allowfullscreen></iframe>
    <p class="video-placeholder">Video: {title}</p>
</div>

{content}
"""
    elif content_type.lower() == "quiz":
        # Format quiz questions
        content = f"""# {title} - Quiz

{content}

<div class="quiz-controls">
    <button class="submit-quiz">Submit Answers</button>
    <div class="quiz-results" style="display:none;">
        <h3>Quiz Results</h3>
        <p>Your score: <span class="score">0</span>%</p>
    </div>
</div>
"""
    elif content_type.lower() == "assignment" or content_type.lower() == "exercise":
        # Format assignment
        content = f"""# {title} - Assignment

{content}

<div class="assignment-submission">
    <h3>Submit Your Work</h3>
    <textarea placeholder="Enter your response here..."></textarea>
    <button class="submit-assignment">Submit Assignment</button>
</div>
"""
    
    # Convert to HTML
    html = convert_markdown_to_html(
        content,
        use_standardized_images=use_standardized_images
    )
    
    return html

def generate_enhancement_comparison_report(original_content: str, 
                                        enhanced_content: str,
                                        enhancement_details: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate an HTML report comparing original and enhanced content.
    
    Args:
        original_content: Original content (markdown)
        enhanced_content: Enhanced content (markdown)
        enhancement_details: Optional dictionary with enhancement details
        
    Returns:
        HTML report comparing the content
    """
    # Create base HTML
    html = create_html_base("Content Enhancement Comparison")
    
    # Convert both contents to HTML
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'nl2br'])
    original_html = md.convert(original_content)
    enhanced_html = md.convert(enhanced_content)
    
    # Create comparison HTML
    comparison_html = """
    <h1>Content Enhancement Comparison</h1>
    """
    
    # Add enhancement details if provided
    if enhancement_details:
        comparison_html += "<div class='enhancement-details'>\n"
        comparison_html += "<h2>Enhancement Details</h2>\n"
        
        if "changes" in enhancement_details:
            comparison_html += "<h3>Changes Made</h3>\n<ul>\n"
            for change in enhancement_details["changes"]:
                comparison_html += f"<li>{change}</li>\n"
            comparison_html += "</ul>\n"
        
        if "metrics" in enhancement_details:
            comparison_html += "<h3>Metrics</h3>\n<ul>\n"
            for key, value in enhancement_details["metrics"].items():
                comparison_html += f"<li><strong>{key}:</strong> {value}</li>\n"
            comparison_html += "</ul>\n"
            
        comparison_html += "</div>\n"
    
    # Add side by side comparison
    comparison_html += """
    <h2>Side-by-Side Comparison</h2>
    <div class="comparison-container" style="display: flex; gap: 20px;">
        <div class="original" style="flex: 1;">
            <h3>Original Content</h3>
            <div class="content-box" style="border: 1px solid #ccc; padding: 15px; background-color: #f9f9f9;">
    """
    comparison_html += original_html
    comparison_html += """
            </div>
        </div>
        <div class="enhanced" style="flex: 1;">
            <h3>Enhanced Content</h3>
            <div class="content-box" style="border: 1px solid #ccc; padding: 15px; background-color: #f9f9f9;">
    """
    comparison_html += enhanced_html
    comparison_html += """
            </div>
        </div>
    </div>
    """
    
    # Insert content into base
    html = html.replace("<!-- Content will be inserted here -->", comparison_html)
    
    return html

class HTMLConverter:
    """HTML conversion utility class for ShowupSquared."""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize HTMLConverter.
        
        Args:
            base_dir: Optional base directory for file operations
        """
        self.base_dir = base_dir
        self.logger = logging.getLogger("html_converter")
    
    def convert_markdown_file(self, 
                            input_path: str, 
                            output_path: str,
                            use_standardized_images: bool = True,
                            include_audio: bool = False) -> bool:
        """
        Convert a Markdown file to HTML.
        
        Args:
            input_path: Path to markdown file
            output_path: Path for output HTML
            use_standardized_images: Whether to use standardized images
            include_audio: Whether to include audio elements
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            # Read markdown file
            with open(input_path, 'r', encoding='utf-8') as file:
                markdown_content = file.read()
            
            # Convert to HTML
            html_content = convert_markdown_to_html(
                markdown_content,
                use_standardized_images=use_standardized_images,
                include_audio=include_audio
            )
            
            # Write HTML file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(html_content)
                
            self.logger.info(f"Converted {input_path} to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error converting {input_path} to HTML: {str(e)}")
            return False