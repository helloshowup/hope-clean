#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Audio processing module for podcast generator.

Handles the conversion of scripts to audio using Azure TTS and SSML enhancement.
"""

import os
import re
import logging
import azure.cognitiveservices.speech as speechsdk
from typing import Dict
from datetime import datetime
from showup_editor_ui.claude_panel.path_utils import get_project_root

logger = logging.getLogger('podcast_generator')


# HD voice marker used to detect Dragon HD voices that only support a subset of SSML tags
HD_MARKER = ":DragonHD"

# Default TTS voice configuration
DEFAULT_TTS_CONFIG = {
    "specialist1": {
        "voice_name": "en-US-Andrew:DragonHDLatestNeural",
        "temperature": "0.25"
    },
    "specialist2": {
        "voice_name": "en-US-Andrew2:DragonHDLatestNeural",
        "temperature": "0.6"
    }
}


def escape_xml(text: str) -> str:
    """Escape XML special characters in text."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def rewrite_markers(text: str) -> str:
    """Convert emphasis and pause markers to SSML tags."""
    # Process emphasis markers
    text = re.sub(r'\[emphasis\]\s*(.*?)\s*(\[\/emphasis\]|\])', 
                r'<emphasis level="moderate">\1</emphasis>', 
                text)
    
    # Process pause markers
    text = re.sub(r'\[pause\]', r'<break time="650ms"/>', text)
    
    # Add pauses at sentence boundaries for technical explanations
    text = re.sub(r'(\&gt;?\s*\.\s+)([A-Z])', r'.\n<break time="350ms"/>\2', text)
    
    # Add slight pauses after commas for more natural speech rhythm
    text = re.sub(r'(\&gt;?\s*,\s+)([a-zA-Z])', r',\n<break time="150ms"/>\2', text)
    
    return text


def enhance_with_ssml(script: str, tts_config: Dict[str, Dict[str, str]] = None) -> str:
    """Transform script dialogue into SSML-enhanced output."""
    if tts_config is None:
        tts_config = DEFAULT_TTS_CONFIG
    
    # Create a valid SSML document
    ssml_output = '<?xml version="1.0"?>\n'
    ssml_output += '<!-- Note: This script may not meet all quality guidelines. Please review carefully. -->\n'
    ssml_output += '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
    ssml_output += 'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">\n'

    # Process each paragraph to identify speaker turns
    paragraphs = script.split('\n\n')
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        # Detect speakers and apply voice-specific SSML
        if re.search(r'Specialist 1:', paragraph, re.IGNORECASE):
            # Extract the actual spoken content
            content = re.sub(r'Specialist 1:', '', paragraph, flags=re.IGNORECASE).strip()
            
            # Apply Specialist 1 (technical expert) voice characteristics
            voice_config = tts_config["specialist1"]
            voice_name = voice_config["voice_name"]
            is_hd = HD_MARKER in voice_name
            
            # Escape XML characters before any processing
            content = escape_xml(content)
            
            if is_hd:
                # For HD voices, use minimal SSML as most tags are unsupported
                # See: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-structure#supported-and-unsupported-ssml-elements-for-azure-ai-speech-hd-voices
                temperature = voice_config.get("temperature", "0.5")
                ssml_output += f'<voice name="{voice_name}" parameters="temperature={temperature}">\n'
                ssml_output += f'<p>{content}</p>\n'
                ssml_output += '</voice>\n\n'
            else:
                # For non-HD voices, apply full SSML enhancement
                ssml_output += '<voice name="' + voice_name + '">\n'
                
                # Only add prosody tags if we have rate or pitch specified
                if "rate" in voice_config or "pitch" in voice_config:
                    rate = voice_config.get("rate", "1.0")
                    pitch = voice_config.get("pitch", "0st")
                    ssml_output += f'<prosody rate="{rate}" pitch="{pitch}">\n'
                    
                    # Process emphasis and pause markers
                    content = rewrite_markers(content)
                    
                    ssml_output += content
                    ssml_output += '\n</prosody>\n'
                else:
                    # No prosody needed
                    content = rewrite_markers(content)
                    ssml_output += content + '\n'
                    
                ssml_output += '</voice>\n\n'
            
        elif re.search(r'Specialist 2:', paragraph, re.IGNORECASE):
            # Extract the actual spoken content
            content = re.sub(r'Specialist 2:', '', paragraph, flags=re.IGNORECASE).strip()
            
            # Apply Specialist 2 (applications expert) voice characteristics
            voice_config = tts_config["specialist2"]
            voice_name = voice_config["voice_name"]
            is_hd = HD_MARKER in voice_name
            
            # Escape XML characters before any processing
            content = escape_xml(content)
            
            if is_hd:
                # For HD voices, use minimal SSML as most tags are unsupported
                temperature = voice_config.get("temperature", "0.5")
                ssml_output += f'<voice name="{voice_name}" parameters="temperature={temperature}">\n'
                ssml_output += f'<p>{content}</p>\n'
                ssml_output += '</voice>\n\n'
            else:
                # For non-HD voices, apply full SSML enhancement
                ssml_output += '<voice name="' + voice_name + '">\n'
                
                # Only add prosody tags if we have rate or pitch specified
                if "rate" in voice_config or "pitch" in voice_config:
                    rate = voice_config.get("rate", "1.0")
                    pitch = voice_config.get("pitch", "0st")
                    ssml_output += f'<prosody rate="{rate}" pitch="{pitch}">\n'
                    
                    # Process emphasis markers and other SSML enhancements
                    content = rewrite_markers(content)
                    
                    # Additional handling for questions that's only needed for non-HD voices
                    content = re.sub(r'(\&gt;?\s*\?\s+)([A-Z])', 
                                    r'?\n<break time="400ms"/>\2', 
                                    content)
                    
                    ssml_output += content
                    ssml_output += '\n</prosody>\n'
                else:
                    # No prosody needed
                    content = rewrite_markers(content)
                    # Additional handling for questions that's only needed for non-HD voices
                    content = re.sub(r'(\&gt;?\s*\?\s+)([A-Z])', 
                                    r'?\n<break time="400ms"/>\2', 
                                    content)
                    ssml_output += content + '\n'
                
                ssml_output += '</voice>\n\n'
            
        else:
            # Non-dialogue content - wrap in voice tags to make valid SSML
            non_dialogue_content = escape_xml(paragraph)
            # Use the first specialist voice for any narrator or non-dialogue text
            voice_config = tts_config["specialist1"]
            voice_name = voice_config["voice_name"]
            is_hd = HD_MARKER in voice_name
            
            if is_hd:
                temperature = voice_config.get("temperature", "0.25") # Lower temperature for narration
                ssml_output += f'<voice name="{voice_name}" parameters="temperature={temperature}">\n'
                ssml_output += f'<p>{non_dialogue_content}</p>\n'
                ssml_output += '</voice>\n\n'
            else:
                ssml_output += '<voice name="' + voice_name + '">\n'
                
                # Only add prosody tags if we have rate or pitch specified
                if "rate" in voice_config or "pitch" in voice_config:
                    rate = voice_config.get("rate", "1.0")
                    pitch = voice_config.get("pitch", "0st")
                    ssml_output += f'<prosody rate="{rate}" pitch="{pitch}">\n'
                    ssml_output += f'{non_dialogue_content}\n'
                    ssml_output += '\n</prosody>\n'
                else:
                    ssml_output += f'{non_dialogue_content}\n'
                
                ssml_output += '</voice>\n\n'
    
    ssml_output += '</speak>'
    
    # Save SSML to debug file
    debug_dir = os.path.join(str(get_project_root()), "showup_core", "generated_podcasts")
    os.makedirs(debug_dir, exist_ok=True)
    debug_file = os.path.join(debug_dir, f"ssml_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml")
    with open(debug_file, 'w', encoding='utf-8') as f:
        f.write(ssml_output)
    logger.info(f"SSML debug file saved to: {debug_file}")
    
    return ssml_output


def convert_to_audio(script: str, tts_config: Dict[str, Dict[str, str]] = None, output_dir: str = None) -> str:
    """Convert script to audio using Azure TTS with SSML enhancement.
    
    For larger scripts, automatically chunks the content to prevent Azure TTS timeouts.
    
    Args:
        script: The script content to convert to audio
        tts_config: Optional voice configuration dictionary
        output_dir: Optional output directory path. If None, uses default directory
        
    Returns:
        Path to the generated audio file or error message
    """
    if tts_config is None:
        tts_config = DEFAULT_TTS_CONFIG
        
    try:
        # Create timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine output directory
        if not output_dir:
            # Use default location
            output_dir = os.path.join(str(get_project_root()), "showup_core", "generated_podcasts")
        
        # Make sure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        final_output_path = os.path.join(output_dir, f"podcast_{timestamp}.mp3")
        
        # Get Azure credentials
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        service_region = os.getenv("AZURE_SPEECH_REGION")
        
        if not speech_key or not service_region:
            error_msg = "Error: Azure Speech credentials not found in environment variables."
            logger.error(error_msg)
            return error_msg
        
        # Generate enhanced SSML content
        ssml_content = enhance_with_ssml(script, tts_config)
        
        # Save SSML to debug file for inspection if needed
        ssml_debug_path = os.path.join(output_dir, f"ssml_debug_{timestamp}.xml")
        with open(ssml_debug_path, "w", encoding="utf-8") as f:
            f.write(ssml_content)
            
        logger.info(f"SSML content saved to {ssml_debug_path}")
        
        # Check if the script is large (> 5000 characters is a reasonable threshold)
        # If so, we'll process it in chunks to avoid Azure timeouts
        if len(ssml_content) > 5000:
            logger.info(f"Large script detected ({len(ssml_content)} characters). Processing in chunks.")
            return _process_large_script(script, ssml_content, speech_key, service_region, output_dir, timestamp, tts_config)
        
        # For smaller scripts, use the standard approach
        return _process_single_request(ssml_content, speech_key, service_region, final_output_path)
            
    except Exception as e:
        import traceback
        error_msg = f"Error converting to audio with Azure: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg


def _process_single_request(ssml_content: str, speech_key: str, service_region: str, 
                           output_path: str) -> str:
    """Process a single TTS request for smaller scripts."""
    # Configure Azure TTS
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    
    # Configure audio output
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    
    # Create speech synthesizer
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    # Process with Azure TTS
    logger.info("Processing script with Azure TTS")
    result = synthesizer.speak_ssml_async(ssml_content).get()
    
    # Check result
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        logger.info(f"Audio file saved to {output_path}")
        return output_path
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        error_msg = f"TTS canceled: {cancellation.reason}\n"
        error_msg += f"Error details: {cancellation.error_details}"
        logger.error(error_msg)
        return error_msg
    else:
        error_msg = f"TTS failed: {result.reason}"
        logger.error(error_msg)
        return error_msg


def _process_large_script(script: str, full_ssml: str, speech_key: str, service_region: str, 
                         output_dir: str, timestamp: str, tts_config: Dict[str, Dict[str, str]]) -> str:
    """Process a large script by splitting it into manageable chunks."""
    try:
        # Split the script into manageable chunks by speaker turns
        paragraphs = script.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Target around 2000 characters per chunk (about 2-3 minutes of audio)
        # This size is a balance between avoiding timeouts and minimizing join points
        chunk_size = 2000
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # Always keep speaker turns together
            if current_length + len(para) > chunk_size and current_chunk:
                # Save current chunk and start a new one
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = len(para)
            else:
                current_chunk.append(para)
                current_length += len(para)
                
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        logger.info(f"Split script into {len(chunks)} chunks for processing")
        
        # Process each chunk and collect the audio files
        temp_files = []
        final_output_path = os.path.join(output_dir, f"podcast_{timestamp}.mp3")
        
        for i, chunk in enumerate(chunks):
            # Generate SSML for this chunk
            chunk_ssml = enhance_with_ssml(chunk, tts_config)
            
            # Save SSML to debug file for inspection
            chunk_debug_path = os.path.join(output_dir, f"ssml_chunk_{i}_{timestamp}.xml")
            with open(chunk_debug_path, "w", encoding="utf-8") as f:
                f.write(chunk_ssml)
                
            # Process with Azure TTS
            chunk_output_path = os.path.join(output_dir, f"chunk_{i}_{timestamp}.mp3")
            
            # Configure Azure
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
            audio_config = speechsdk.audio.AudioOutputConfig(filename=chunk_output_path)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            result = synthesizer.speak_ssml_async(chunk_ssml).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(f"Chunk {i+1} audio saved to {chunk_output_path}")
                temp_files.append(chunk_output_path)
            else:
                error_msg = f"Failed to synthesize chunk {i+1}: {result.reason}"
                if result.reason == speechsdk.ResultReason.Canceled:
                    error_msg += f" - {result.cancellation_details.error_details}"
                logger.error(error_msg)
                return error_msg
        
        # Concatenate the audio files using FFmpeg directly
        try:
            if not temp_files:
                return "Error: No audio chunks were successfully generated"
            
            # Create a text file listing all input files for FFmpeg
            concat_list_path = os.path.join(output_dir, f"concat_list_{timestamp}.txt")
            with open(concat_list_path, 'w', encoding='utf-8') as f:
                for audio_file in temp_files:
                    f.write(f"file '{audio_file}'\n")
            
            logger.info(f"Combining {len(temp_files)} audio chunks using FFmpeg")
            
            # Use FFmpeg to concatenate the files
            import subprocess
            # Instead of using -c copy (which requires identical streams), we'll re-encode
            # to ensure compatibility between chunks
            ffmpeg_cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_path, 
                          "-c:a", "libmp3lame", "-q:a", "4", final_output_path]
            
            process = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode != 0:
                logger.warning(f"FFmpeg concatenation failed: {process.stderr}")
                # Fallback to keeping all chunks if ffmpeg fails
                return "\n".join(["Multiple audio files generated (concatenation failed):"] + temp_files)
                
            # Clean up temp files if successful
            for file in temp_files:
                try:
                    os.remove(file)
                except Exception as e:
                    logger.warning(f"Could not delete temp file {file}: {str(e)}")
                    
            try:
                os.remove(concat_list_path)  # Clean up the concat list file
            except Exception:
                pass
                
            logger.info(f"Final audio file saved to {final_output_path}")
            return final_output_path
            
        except Exception as e:
            import traceback
            logger.warning(f"Error during audio concatenation: {str(e)}\n{traceback.format_exc()}")
            # Return all chunk files if concatenation fails
            return "\n".join(["Multiple audio files generated (could not combine):"] + temp_files)
        
    except Exception as e:
        import traceback
        error_msg = f"Error processing large script: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg
