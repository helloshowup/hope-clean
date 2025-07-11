#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Audio processing module for fitness instructor voiceover.

Handles the conversion of fitness instruction scripts to audio using Azure TTS and SSML enhancement.
Uses DragonHD voice for high-quality audio outputs, with a low temperature setting (0.25) to ensure
consistent performance delivery with minimal variation between runs - critical for fitness instruction
where clear, predictable pronunciation of exercise terms is essential.
"""

import os
import re
import logging
import azure.cognitiveservices.speech as speechsdk
from typing import Dict, Optional
from datetime import datetime
from showup_editor_ui.claude_panel.path_utils import get_project_root

# Import common audio processing utilities
from .audio_processor import escape_xml

logger = logging.getLogger('fitness_instructor_voiceover')

# Default TTS voice configuration for fitness instructor
# Uses a single voice model with a lower temperature for consistent delivery
DEFAULT_TTS_CONFIG = {
    "fitness_instructor": {
        "voice_name": "en-US-Andrew:DragonHDLatestNeural",
        "temperature": "0.25"
    }
}


def convert_break_duration(duration_str: str) -> str:
    """Convert a pause duration string to milliseconds for SSML break tags.
    
    Handles formats like '2s', '500ms', or defaults to 650ms if no duration specified.
    """
    if not duration_str:
        return "650ms"  # Default pause duration
    
    # Strip any whitespace
    duration_str = duration_str.strip()
    
    # If already in milliseconds format, return as is
    if duration_str.endswith("ms"):
        try:
            # Verify it's a valid number
            ms_value = int(duration_str[:-2])
            return f"{ms_value}ms"
        except ValueError:
            logger.warning(f"Invalid millisecond format: {duration_str}, using default")
            return "650ms"
    
    # If in seconds format, convert to milliseconds
    if duration_str.endswith("s"):
        try:
            seconds = float(duration_str[:-1])
            ms_value = int(seconds * 1000)
            return f"{ms_value}ms"
        except ValueError:
            logger.warning(f"Invalid seconds format: {duration_str}, using default")
            return "650ms"
    
    # If just a number, assume seconds and convert
    try:
        seconds = float(duration_str)
        ms_value = int(seconds * 1000)
        return f"{ms_value}ms"
    except ValueError:
        logger.warning(f"Invalid duration format: {duration_str}, using default")
        return "650ms"


def rewrite_markers(text: str) -> str:
    """Convert emphasis and pause markers to SSML tags with enhanced features."""
    # Process emphasis markers with optional strength level
    # Format: [emphasis] or [emphasis strong]
    text = re.sub(r'\[emphasis(?: (strong|moderate|reduced))?\]\s*(.*?)\s*(\[\/emphasis\]|\])', 
                lambda m: f'<emphasis level="{m.group(1) or "moderate"}">{m.group(2)}</emphasis>', 
                text)
    
    # Process variable-length pause markers
    # Format: [pause] or [pause 2s] or [pause 1500ms]
    text = re.sub(r'\[pause(?: ([^\]]+))?\]', 
                lambda m: f'<break time="{convert_break_duration(m.group(1))}"/>', 
                text)
    
    # Add pauses at sentence boundaries for better pacing
    text = re.sub(r'(\&gt;?\s*\.\s+)([A-Z])', r'.\n<break time="350ms"/>\2', text)
    
    # Add slight pauses after commas for more natural speech rhythm
    text = re.sub(r'(\&gt;?\s*,\s+)([a-zA-Z])', r',\n<break time="150ms"/>\2', text)
    
    # Add prosody boost for rep counting lines (specifically for fitness instructions)
    # Match lines starting with number words (One, Two, ..., Ten)
    text = re.sub(r'^(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\b(.+)$', 
                r'<prosody rate="+5%" volume="+1dB">\1\2</prosody>', 
                text, flags=re.MULTILINE)
    
    return text


def enhance_fitness_script_with_ssml(script: str, tts_config: Optional[Dict[str, Dict[str, str]]] = None) -> str:
    """Transform fitness instruction script into SSML-enhanced output."""
    if tts_config is None:
        tts_config = DEFAULT_TTS_CONFIG
    
    # Create a valid SSML document
    ssml_output = '<?xml version="1.0"?>\n'
    ssml_output += '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
    ssml_output += 'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">\n'

    # Process each paragraph 
    paragraphs = script.split('\n\n')
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        # Apply fitness instructor voice characteristics
        voice_config = tts_config["fitness_instructor"]
        voice_name = voice_config["voice_name"]
        temperature = voice_config.get("temperature", "0.25")
        
        # Escape XML characters before any processing
        content = escape_xml(paragraph)
        
        # Apply SSML formatting
        # For Dragon HD voices, use minimal SSML as most tags are unsupported
        ssml_output += f'<voice name="{voice_name}" parameters="temperature={temperature}">\n'
        
        # Process emphasis and pause markers
        content = rewrite_markers(content)
        
        ssml_output += f'<p>{content}</p>\n'
        ssml_output += '</voice>\n\n'
    
    ssml_output += '</speak>'
    return ssml_output


def convert_fitness_script_to_audio(script: str, tts_config: Optional[Dict[str, Dict[str, str]]] = None, 
                                 output_dir: Optional[str] = None) -> str:
    """Convert fitness instruction script to audio using Azure TTS with SSML enhancement."""
    # Use fitness-specific SSML enhancement
    ssml_script = enhance_fitness_script_with_ssml(script, tts_config)
    
    # If no output directory is specified, use the default generated_fitness_audio directory
    if output_dir is None:
        output_dir = os.path.join(str(get_project_root()), "showup_core", "generated_fitness_audio")
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"fitness_instruction_{timestamp}.mp3"
    output_path = os.path.join(output_dir, output_filename)
    
    # Convert to audio using the base function but with fitness-specific settings
    try:
        # Get subscription key and region from environment variables
        speech_key = os.environ.get("SPEECH_KEY")
        speech_region = os.environ.get("SPEECH_REGION")
        
        if not speech_key or not speech_region:
            logger.error("Azure Speech credentials not found in environment variables")
            raise ValueError("Missing Azure Speech credentials. Set SPEECH_KEY and SPEECH_REGION environment variables.")
        
        # Configure speech synthesizer
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
        
        # Configure audio output
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
        
        # Create speech synthesizer
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        
        # Synthesize speech
        result = speech_synthesizer.speak_ssml_async(ssml_script).get()
        
        # Check result
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info(f"Speech synthesis completed for {output_filename}")
            return output_path
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            logger.error(f"Speech synthesis canceled: {cancellation_details.reason}")
            logger.error(f"Speech synthesis error details: {cancellation_details.error_details}")
            raise Exception(f"Speech synthesis failed: {cancellation_details.reason}")
        else:
            logger.warning(f"Speech synthesis result: {result.reason}")
            return output_path
    
    except Exception as e:
        logger.error(f"Error in speech synthesis: {str(e)}")
        raise
