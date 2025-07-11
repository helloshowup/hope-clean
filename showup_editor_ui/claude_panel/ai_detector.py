"""AI Detection Module for ClaudeAIPanel"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
import json
import re

try:
    from nicegui import ui
except Exception:  # pragma: no cover - optional dependency
    class _DummyUI:
        @staticmethod
        def toast(*args, **kwargs):
            pass

    ui = _DummyUI()

from .path_utils import get_project_root
from showup_core.utils import cache_utils, claude_api
from claude_api import CLAUDE_MODELS

# Get project root once for local file references
project_root = get_project_root()

# Alias commonly used functions
get_cache_instance = cache_utils.get_cache_instance
detect_ai_content = claude_api.generate_with_claude_sonnet
rewrite_ai_content = claude_api.generate_with_claude_diff_edit

# Get logger
logger = logging.getLogger("AIDetector")

class AIDetector:
    """Handles AI detection functionality for the ClaudeAIPanel."""
    
    def __init__(self, parent):
        """Initialize the AI detector panel.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.analyzing = False
        self.analysis_thread = None
        self.analyzed_files = {}
        self.result_tabs = {}
        self.use_uk_spelling = False  # Default to US spelling
        self.sentence_patterns_only = False  # Default to all patterns
        self.word_patterns_only = False  # Default to all patterns, not just word patterns
        
        # Load AI pattern definitions
        self.ai_patterns = self._load_ai_patterns()
        
    def _load_ai_patterns(self):
        """Load AI pattern definitions from the patterns file."""
        try:
            # Path to the patterns file
            patterns_file = os.path.join(
                str(project_root),
                "showup-editor-ui",
                "data",
                "input",
                "ai_patterns.json",
            )
            
            # Create default patterns file if it doesn't exist
            if not os.path.exists(patterns_file):
                os.makedirs(os.path.dirname(patterns_file), exist_ok=True)
                default_patterns = {
                    "patterns": [
                        {
                            "category": "Common AI Phrases",
                            "patterns": [
                                "(?:\\bas an AI\\b|\\bas an artificial intelligence\\b)",
                                "I don't have personal",
                                "I don't have the ability to",
                                "I cannot browse",
                                "my knowledge (?:is limited to|cutoff|base)",
                                "I don't have (?:access to|the capability to|the ability to)",
                                "\\bcertainly\\b.{0,10}\\bhere\\b.{0,20}\\b(?:summary|overview|explanation|analysis|breakdown|guide)"
                            ]
                        },
                        {
                            "category": "Repetitive Structures",
                            "patterns": [
                                "\\b(?:First|1)[.,:].*?\\b(?:Second|2)[.,:].*?\\b(?:Third|3)[.,:].*?\\b(?:Fourth|4)[.,:].*?\\b(?:Fifth|5)[.,:].*?\\b(?:Sixth|6)[.,:].*?\\b(?:Seventh|7)[.,:]\\b",
                                "\\b(?:Pros|Advantages)[.,:].*?\\b(?:Cons|Disadvantages)[.,:]\\b",
                                "(?:\\bin conclusion\\b|\\bto summarize\\b|\\bin summary\\b).*?(?:\\bthank you\\b|\\bi hope this helps\\b)"
                            ]
                        },
                        {
                            "category": "Overused Transitions",
                            "patterns": [
                                "\\b(?:Note that|Importantly|Specifically|In particular|Notably|It's worth noting|Keep in mind|Remember that)\\b",
                                "\\b(?:however|nevertheless|on the other hand)\\b.{0,40}\\b(?:however|nevertheless|on the other hand)\\b.{0,40}\\b(?:however|nevertheless|on the other hand)\\b"
                            ]
                        }
                    ],
                    "phrases": [
                        "as an AI",
                        "I hope this helps",
                        "please let me know",
                        "if you have any questions",
                        "I'd be happy to"
                    ]
                }
                
                with open(patterns_file, 'w', encoding='utf-8') as f:
                    json.dump(default_patterns, f, indent=4)
                
                logger.info(f"Created default AI detection patterns file at {patterns_file}")
            
            # Load the patterns file
            with open(patterns_file, 'r', encoding='utf-8') as f:
                patterns_data = json.load(f)
                
            logger.info(f"Loaded AI detection patterns from {patterns_file}")
            return patterns_data
            
        except Exception as e:
            logger.error(f"Error loading AI patterns: {str(e)}")
            # Return default empty patterns
            return {"patterns": [], "phrases": []}
        
    def setup_ai_detect_tab(self):
        """Set up the AI Detection tab."""
        tab = self.parent.ai_detect_tab
        
        # Create main frame for controls and results
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create top frame for controls
        self.controls_frame = ttk.LabelFrame(main_frame, text="AI Detection Controls")
        self.controls_frame.pack(fill="x", padx=5, pady=5)
        
        # Add analyze button
        analyze_btn = ttk.Button(self.controls_frame, text="Analyze & Auto-Fix Selected Files", 
                              command=self.analyze_selected_files)
        analyze_btn.pack(side="left", padx=5, pady=5)
        
        # Add UK/US spelling toggle
        spelling_frame = ttk.Frame(self.controls_frame)
        spelling_frame.pack(side="left", padx=5, pady=5)
        
        self.spelling_var = tk.BooleanVar(value=self.use_uk_spelling)
        spelling_checkbox = ttk.Checkbutton(spelling_frame, text="Use UK Spelling", 
                                          variable=self.spelling_var,
                                          command=self._toggle_spelling)
        spelling_checkbox.pack(side="left")
        
        # Show examples of differences
        spelling_info = ttk.Label(spelling_frame, text="(e.g., color → colour)")
        spelling_info.pack(side="left", padx=5)
        
        # Add sentence patterns only toggle
        patterns_frame = ttk.Frame(self.controls_frame)
        patterns_frame.pack(side="left", padx=5, pady=5)
        
        self.sentence_patterns_var = tk.BooleanVar(value=self.sentence_patterns_only)
        sentence_patterns_checkbox = ttk.Checkbutton(patterns_frame, text="Sentence Patterns Only", 
                                                 variable=self.sentence_patterns_var,
                                                 command=self._toggle_sentence_patterns)
        sentence_patterns_checkbox.pack(side="left")
        
        # Show tooltip for sentence patterns
        patterns_info = ttk.Label(patterns_frame, text="(Only use sentence-level patterns)")
        patterns_info.pack(side="left", padx=5)
        
        # Add word patterns only toggle
        word_patterns_frame = ttk.Frame(self.controls_frame)
        word_patterns_frame.pack(side="left", padx=5, pady=5)
        
        self.word_patterns_var = tk.BooleanVar(value=self.word_patterns_only)
        word_patterns_checkbox = ttk.Checkbutton(word_patterns_frame, text="Word Patterns Only", 
                                             variable=self.word_patterns_var,
                                             command=self._toggle_word_patterns)
        word_patterns_checkbox.pack(side="left")
        
        # Show tooltip for word patterns
        word_patterns_info = ttk.Label(word_patterns_frame, text="(Only use overused AI words)")
        word_patterns_info.pack(side="left", padx=5)
        
        # Add status label
        self.ai_status_label = ttk.Label(self.controls_frame, text="Select files from the library panel and click Analyze")
        self.ai_status_label.pack(side="left", padx=5, pady=5)
        
        # Add progress bar
        self.ai_progress = ttk.Progressbar(self.controls_frame, mode="determinate")
        self.ai_progress.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # Create results notebook
        self.results_frame = ttk.LabelFrame(main_frame, text="Analysis Results")
        self.results_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.results_notebook = ttk.Notebook(self.results_frame)
        self.results_notebook.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _toggle_spelling(self):
        """Toggle between UK and US spelling."""
        self.use_uk_spelling = self.spelling_var.get()
        logger.info(f"Set spelling preference to {'UK' if self.use_uk_spelling else 'US'}")
    
    def _toggle_sentence_patterns(self):
        """Toggle between all patterns and sentence patterns only."""
        self.sentence_patterns_only = self.sentence_patterns_var.get()
        
        # If turning on sentence patterns only, make sure word patterns only is off
        if self.sentence_patterns_only and self.word_patterns_only:
            self.word_patterns_only = False
            self.word_patterns_var.set(False)
        
        logger.info(f"Set pattern mode to {'sentence patterns only' if self.sentence_patterns_only else 'all patterns'}")
    
    def _toggle_word_patterns(self):
        """Toggle between all patterns and word patterns only."""
        self.word_patterns_only = self.word_patterns_var.get()
        
        # If turning on word patterns only, make sure sentence patterns only is off
        if self.word_patterns_only and self.sentence_patterns_only:
            self.sentence_patterns_only = False
            self.sentence_patterns_var.set(False)
        
        logger.info(f"Set pattern mode to {'word patterns only' if self.word_patterns_only else 'all patterns'}")
    
    def analyze_selected_files(self):
        """Analyze the files selected in the main library panel."""
        # Get files selected in the main library panel
        selected_files = []
        
        if hasattr(self.parent, "file_tree") and self.parent.file_tree:
            for item_id in self.parent.file_tree.selection():
                item_values = self.parent.file_tree.item(item_id, "values")
                if item_values and len(item_values) > 1:
                    path = item_values[0]
                    item_type = item_values[1] if len(item_values) > 1 else ""
                    
                    # Only process files, not directories
                    if item_type != "directory" and os.path.isfile(path):
                        selected_files.append(path)
        
        # Check if any files were selected
        if not selected_files:
            messagebox.showinfo("No Files Selected", "Please select files in the library panel first.")
            return
        
        # Clear previous results
        for tab in self.results_notebook.tabs():
            self.results_notebook.forget(tab)
        
        self.analyzed_files = {}
        self.result_tabs = {}
        
        # Update UI
        self.ai_status_label.config(text=f"Analyzing and fixing {len(selected_files)} files...")
        self.ai_progress["value"] = 0
        self.ai_progress["maximum"] = len(selected_files) * 2  # Analysis + Rewriting
        
        # Start analysis in a thread
        self.analyzing = True
        self.analysis_thread = threading.Thread(target=self._analyze_and_fix_files_thread, args=(selected_files,))
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        
        logger.info(f"Started AI detection analysis and fixing for {len(selected_files)} files")
    
    def _analyze_and_fix_files_thread(self, file_paths):
        """Thread function for analyzing and automatically fixing multiple files."""
        try:
            total_files = len(file_paths)
            processed = 0
            
            for file_path in file_paths:
                try:
                    # Update progress
                    self.parent.after(0, lambda p=processed, t=total_files: 
                                     self._update_ai_analysis_progress(p, t, "Analyzing"))
                    
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    # Analyze file for AI content using regex
                    detection_result = self._detect_ai_patterns(file_content)
                    
                    # Store result
                    self.analyzed_files[file_path] = detection_result
                    
                    # Add result tab
                    self.parent.after(0, lambda p=file_path, r=detection_result: self._add_result_tab(p, r))
                    
                    # If AI patterns were detected, automatically rewrite content
                    if detection_result["detected"]:
                        processed += 1
                        self.parent.after(0, lambda p=processed, t=total_files: 
                                         self._update_ai_analysis_progress(p, t, "Rewriting"))
                        
                        # Rewrite and update file automatically
                        self._rewrite_content(file_path, detection_result)
                    
                except Exception as e:
                    logger.error(f"Error analyzing file {file_path}: {str(e)}")
                    self.parent.after(0, lambda p=file_path, e=str(e): self._add_error_tab(p, e))
                
                processed += 1
                self.parent.after(0, lambda p=processed, t=total_files * 2: 
                                 self._update_ai_analysis_progress(p, t))
            
            # Analysis complete
            self.parent.after(0, self._analysis_complete)
            
        except Exception as e:
            logger.error(f"Error in AI analysis thread: {str(e)}")
            self.parent.after(0, lambda: self._analysis_error(str(e)))
    
    def _detect_ai_patterns(self, content):
        """Detect AI patterns in the content using regex."""
        detected_patterns = []
        
        # Pattern weights by category (higher values indicate stronger AI signals)
        category_weights = {
            "Common Phrases": 1.0,
            "Scenario_Prompts": 2.0,  # Weigh these more heavily
            "Framework_Language": 1.5,
            "Comparisons": 1.2,
            "Welcome_Phrases": 1.8,
            "Default": 1.0  # Default weight for unspecified categories
        }
        
        try:
            # Check for each pattern in the patterns array
            if "patterns" in self.ai_patterns:
                for category_data in self.ai_patterns["patterns"]:
                    category = category_data.get("category", "Unknown")
                    patterns = category_data.get("patterns", [])
                    pattern_type = category_data.get("type", "")
                    
                    # Skip non-sentence patterns if sentence_patterns_only is enabled
                    if self.sentence_patterns_only and pattern_type != "sentence":
                        continue
                        
                    # Skip non-word patterns if word_patterns_only is enabled
                    if self.word_patterns_only and pattern_type != "word":
                        continue
                    
                    # Get weight for this category (or use default)
                    weight = category_weights.get(category, category_weights["Default"])
                    
                    for pattern in patterns:
                        try:
                            regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
                            matches = list(regex.finditer(content))
                            
                            if matches:
                                for match in matches:
                                    detected_patterns.append({
                                        "pattern": pattern,
                                        "description": f"AI pattern from category: {category}",
                                        "match": match.group(0),
                                        "start": match.start(),
                                        "end": match.end(),
                                        "category": category,
                                        "weight": weight  # Add weight to the pattern
                                    })
                        except Exception as e:
                            logger.error(f"Error with regex pattern '{pattern}': {str(e)}")
            
            # Also check for simple phrases (skip if sentence_patterns_only is enabled)
            if "phrases" in self.ai_patterns and not self.sentence_patterns_only:
                for phrase in self.ai_patterns["phrases"]:
                    if isinstance(phrase, str) and phrase.strip():
                        try:
                            # Create a regex that matches the phrase as a whole word
                            regex = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
                            matches = list(regex.finditer(content))
                            
                            if matches:
                                for match in matches:
                                    detected_patterns.append({
                                        "pattern": phrase,
                                        "description": "Common AI phrase",
                                        "match": match.group(0),
                                        "start": match.start(),
                                        "end": match.end(),
                                        "category": "Common Phrases",
                                        "weight": category_weights.get("Common Phrases", 1.0)  # Add weight
                                    })
                        except Exception as e:
                            logger.error(f"Error with phrase '{phrase}': {str(e)}")
            
            # Sort patterns by position in text
            detected_patterns.sort(key=lambda x: x["start"])
            
            # Find alternatives for detected patterns
            alternatives = {}
            if "alternatives" in self.ai_patterns and detected_patterns:
                alt_dict = self.ai_patterns["alternatives"]
                for pattern in detected_patterns:
                    match_text = pattern["match"].lower()
                    if match_text in alt_dict:
                        alternatives[match_text] = alt_dict[match_text]
            
            # Calculate proximity clusters (patterns that are close together)
            proximity_clusters = []
            if len(detected_patterns) > 1:
                current_cluster = [detected_patterns[0]]
                proximity_threshold = 100  # Characters between patterns to be considered "close"
                
                for i in range(1, len(detected_patterns)):
                    prev_pattern = detected_patterns[i-1]
                    curr_pattern = detected_patterns[i]
                    
                    # If patterns are close, add to current cluster
                    if curr_pattern["start"] - prev_pattern["end"] < proximity_threshold:
                        current_cluster.append(curr_pattern)
                    else:
                        # Start a new cluster if this one has multiple patterns
                        if len(current_cluster) > 1:
                            proximity_clusters.append(current_cluster)
                        current_cluster = [curr_pattern]
                
                # Add the last cluster if it has multiple patterns
                if len(current_cluster) > 1:
                    proximity_clusters.append(current_cluster)
            
            # Calculate an overall AI score using pattern weights and proximity
            total_weight = sum(pattern["weight"] for pattern in detected_patterns)
            base_score = total_weight / max(1, len(content) / 1000)  # Normalize by text length
            
            # Add proximity bonus
            proximity_bonus = 0
            for cluster in proximity_clusters:
                # More patterns close together = higher bonus
                cluster_size = len(cluster)
                cluster_weight = sum(p["weight"] for p in cluster)
                proximity_bonus += (cluster_size * 0.5) * (cluster_weight / cluster_size)
            
            ai_score = base_score + proximity_bonus
            
            # Prepare result
            result = {
                "detected": len(detected_patterns) > 0,
                "patterns": detected_patterns,
                "count": len(detected_patterns),
                "content": content,  # Include original content
                "ai_score": round(ai_score, 2),  # Add AI score
                "proximity_clusters": len(proximity_clusters),  # Number of pattern clusters
                "alternatives": alternatives  # Add suggested alternatives
            }
            
            if detected_patterns:
                # Extract portions of the text with detected patterns for the report
                excerpts = []
                for pattern in detected_patterns:
                    start = max(0, pattern["start"] - 50)  # 50 chars of context before
                    end = min(len(content), pattern["end"] + 50)  # 50 chars after
                    excerpt = content[start:end]
                    excerpts.append({
                        "excerpt": excerpt,
                        "pattern": pattern["pattern"],
                        "category": pattern["category"],
                        "weight": pattern["weight"]  # Include pattern weight
                    })
                
                result["excerpts"] = excerpts
                logger.info(f"Detected {len(detected_patterns)} AI patterns with score {ai_score:.2f}")
            else:
                logger.info("No AI patterns detected")
            
            return result
            
        except Exception as e:
            error_msg = f"Error detecting AI patterns: {str(e)}"
            logger.error(error_msg)
            return {"detected": False, "patterns": [], "error": str(e), "content": content}
    
    def _update_ai_analysis_progress(self, processed, total, status="Processing"):
        """Update progress indicators for AI analysis."""
        self.ai_progress.config(value=processed)
        self.ai_progress_label = self.ai_status_label
        self.ai_progress_label.config(text=f"{status} {processed} of {total} files")
    
    def _analysis_complete(self):
        """Called when AI analysis is complete."""
        self.analyzing = False
        self.ai_status_label.config(text="Analysis and fixing complete")
        
        logger.info(f"AI detection analysis complete for {len(self.analyzed_files)} files")
    
    def _analysis_error(self, error_msg):
        """Called when AI analysis encounters an error."""
        self.analyzing = False
        self.ai_status_label.config(text=f"Error: {error_msg}")
        
        logger.error(f"AI detection analysis error: {error_msg}")
    
    def _add_result_tab(self, file_path, analysis_result):
        """Add a tab for a file analysis result."""
        file_name = os.path.basename(file_path)
        
        # Create a frame for this result
        result_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(result_frame, text=file_name)
        
        # Create the result view
        result_view = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, height=20)
        result_view.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Format the result nicely
        if "error" in analysis_result:
            result_view.insert(tk.END, f"Error analyzing {file_name}:\n{analysis_result['error']}")
        else:
            if analysis_result["detected"]:
                result_view.insert(tk.END, f"AI PATTERNS DETECTED in {file_name}\n")
                result_view.insert(tk.END, f"Found {analysis_result['count']} potential AI patterns.\n\n")
                
                result_view.insert(tk.END, "PATTERN SUMMARY:\n")
                categories = {}
                for pattern in analysis_result["patterns"]:
                    category = pattern["category"]
                    if category not in categories:
                        categories[category] = 0
                    categories[category] += 1
                
                for category, count in categories.items():
                    result_view.insert(tk.END, f"- {category}: {count} instances\n")
                
                result_view.insert(tk.END, "\nDETAILED PATTERNS:\n")
                for i, pattern in enumerate(analysis_result["patterns"]):
                    result_view.insert(tk.END, f"{i+1}. Category: {pattern['category']}\n")
                    result_view.insert(tk.END, f"   Pattern: {pattern['pattern']}\n")
                    result_view.insert(tk.END, f"   Match: {pattern['match']}\n\n")
                
                result_view.insert(tk.END, "REWRITING: Auto-fixing content to remove AI patterns...\n")
            else:
                result_view.insert(tk.END, f"No AI patterns detected in {file_name}. Content appears to be human-written.")
        
        # Make read-only
        result_view.config(state="disabled")
        
        # Store the tab for later updates
        self.result_tabs[file_path] = result_view
    
    def _add_error_tab(self, file_path, error_message):
        """Add an error tab for a file that failed analysis."""
        file_name = os.path.basename(file_path)
        
        # Create a frame for this result
        result_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(result_frame, text=f"{file_name} (Error)")
        
        # Create the result view
        result_view = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, height=20)
        result_view.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Show error
        result_view.insert(tk.END, f"Error analyzing {file_name}:\n\n{error_message}")
        
        # Make read-only
        result_view.config(state="disabled")
    
    def _rewrite_content(self, file_path, detection_result):
        """Rewrite AI-detected content using Claude."""
        if not file_path or not detection_result["detected"]:
            return
        
        try:
            content = detection_result["content"]
            
            # Create prompt for rewriting
            prompt = self._create_rewriting_prompt(detection_result)
            
            # Rewrite content using Claude's diff edit
            try:
                rewritten_content = rewrite_ai_content(
                    prompt=prompt,
                    original_content=content,
                    system_prompt=self._get_system_prompt(),
                    model=CLAUDE_MODELS["CONTENT_EDIT"],
                    temperature=0.3,
                )["edited_content"]
            except Exception as e:
                logger.error(f"Rewrite failed: {str(e)}")
                ui.toast(f"Rewrite failed: {e}")
                raise
            
            # Save original as backup
            from showup_core.file_utils import create_timestamped_backup

            backup_path = create_timestamped_backup(file_path)
            
            # Save rewritten content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(rewritten_content)
            
            # Update the result tab
            if file_path in self.result_tabs:
                result_view = self.result_tabs[file_path]
                result_view.config(state="normal")
                result_view.insert(tk.END, "\nContent successfully rewritten and saved.\n")
                result_view.insert(tk.END, f"Original backed up to: {os.path.basename(backup_path)}\n")
                result_view.config(state="disabled")
            
            logger.info(f"Rewritten content saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Error rewriting content: {str(e)}")
            if file_path in self.result_tabs:
                result_view = self.result_tabs[file_path]
                result_view.config(state="normal")
                result_view.insert(tk.END, f"\nError rewriting content: {str(e)}\n")
                result_view.config(state="disabled")
    
    def _create_rewriting_prompt(self, detection_result):
        """Create a detailed prompt for rewriting based on detected patterns."""
        prompt = """You are an expert content writer specializing in educational materials. 
I need your help to make this content more natural and human-like while 
preserving all educational value and information.

The content has been flagged for having AI-like patterns. I'll share the specific
patterns detected, and I need you to carefully fix ONLY these issues while maintaining
the original meaning and educational value.

"""
        
        # Add detected patterns to the prompt
        for pattern in detection_result["patterns"]:
            prompt += f"Detected pattern: {pattern['pattern']}\n"
            prompt += f"Category: {pattern['category']}\n"
            prompt += f"Match: {pattern['match']}\n\n"
        
        # Add the original content
        prompt += "Original content:\n"
        prompt += detection_result["content"]
        
        return prompt
    
    def _get_system_prompt(self):
        """Get the system prompt for Claude."""
        if self.use_uk_spelling:
            return "Use UK spelling conventions."
        else:
            return "Use US spelling conventions."

    def analyze_selected_text(self, selected_text):
        """Analyze selected text for AI patterns and display a report.
        
        Args:
            selected_text (str): The text selected by the user to analyze
        
        Returns:
            dict: Analysis results containing detected patterns and statistics
        """
        if not selected_text or not selected_text.strip():
            messagebox.showinfo("No Text Selected", "Please select some text to analyze.")
            logger.warning("User attempted to analyze empty text selection")
            return None
            
        try:
            logger.info("Analyzing selected text for AI writing patterns")
            
            # Analyze selected text for AI patterns
            detection_result = self._detect_ai_patterns(selected_text)
            
            # Create a report tab or update existing one
            self._create_or_update_selected_text_report(detection_result)
            
            # Log results
            if detection_result["detected"]:
                logger.info(f"AI writing analysis complete: Found {detection_result['count']} AI patterns")
            else:
                logger.info("AI writing analysis complete: No AI patterns detected")
            
            # Return the result for potential further processing
            return detection_result
            
        except Exception as e:
            error_msg = f"Error analyzing selected text: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Analysis Error", error_msg)
            return None
    
    def _create_or_update_selected_text_report(self, detection_result):
        """Create or update the report tab for the selected text analysis.
        
        Args:
            detection_result (dict): The detection results from analyze_selected_text
        """
        # Check if we already have a tab for selected text analysis
        selected_text_tab_id = None
        for tab_id in self.results_notebook.tabs():
            if self.results_notebook.tab(tab_id, "text") == "Selected Text Analysis":
                selected_text_tab_id = tab_id
                break
        
        # Create or clear the tab
        if selected_text_tab_id:
            # Clear existing content
            for widget in self.results_notebook.nametowidget(selected_text_tab_id).winfo_children():
                widget.destroy()
            result_frame = self.results_notebook.nametowidget(selected_text_tab_id)
        else:
            # Create a new tab
            result_frame = ttk.Frame(self.results_notebook)
            self.results_notebook.add(result_frame, text="Selected Text Analysis")
            
        # Create the report view
        report_view = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, height=20, width=80)
        report_view.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Format the result as a report
        self._format_analysis_report(report_view, detection_result)
        
        # Make the report view read-only
        report_view.config(state="disabled")
        
        # Select the tab
        tab_id = self.results_notebook.tabs()[-1] if not selected_text_tab_id else selected_text_tab_id
        self.results_notebook.select(tab_id)
    
    def _format_analysis_report(self, text_widget, detection_result):
        """Format the analysis results into a readable report.
        
        Args:
            text_widget (scrolledtext.ScrolledText): The text widget to insert the report into
            detection_result (dict): The detection results from analyze_selected_text
        """
        # Insert header
        text_widget.insert(tk.END, "AI WRITING PATTERN ANALYSIS REPORT\n")
        text_widget.insert(tk.END, "=================================\n\n")
        
        # Insert summary
        if detection_result["detected"]:
            text_widget.insert(tk.END, "RESULT: AI PATTERNS DETECTED\n")
            text_widget.insert(tk.END, f"Found {detection_result['count']} potential AI patterns.\n\n")
        else:
            text_widget.insert(tk.END, "RESULT: NO AI PATTERNS DETECTED\n")
            text_widget.insert(tk.END, "The analyzed text appears to be human-written.\n\n")
        
        # Insert pattern summary by category
        if detection_result["detected"]:
            text_widget.insert(tk.END, "PATTERN SUMMARY BY CATEGORY:\n")
            text_widget.insert(tk.END, "----------------------------\n")
            
            categories = {}
            for pattern in detection_result["patterns"]:
                category = pattern["category"]
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1
            
            for category, count in categories.items():
                text_widget.insert(tk.END, f"• {category}: {count} instances\n")
            
            text_widget.insert(tk.END, "\n")
        
        # Insert detailed pattern matches
        if detection_result["detected"]:
            text_widget.insert(tk.END, "DETAILED PATTERN MATCHES:\n")
            text_widget.insert(tk.END, "------------------------\n")
            
            for i, pattern in enumerate(detection_result["patterns"]):
                text_widget.insert(tk.END, f"{i+1}. Category: {pattern['category']}\n")
                text_widget.insert(tk.END, f"   Pattern: {pattern['pattern']}\n")
                text_widget.insert(tk.END, f"   Match: \"{pattern['match']}\"\n")
                
                # Show context (text around the match)
                if "excerpts" in detection_result and i < len(detection_result["excerpts"]):
                    excerpt = detection_result["excerpts"][i]["excerpt"]
                    # Highlight the match within the excerpt
                    match_text = pattern["match"]
                    match_pos = excerpt.find(match_text)
                    if match_pos >= 0:
                        before = excerpt[:match_pos]
                        after = excerpt[match_pos + len(match_text):]
                        text_widget.insert(tk.END, f"   Context: \"...{before}")
                        text_widget.insert(tk.END, match_text, "highlight")
                        text_widget.insert(tk.END, f"{after}...\"\n")
                    else:
                        text_widget.insert(tk.END, f"   Context: \"{excerpt}\"\n")
                
                text_widget.insert(tk.END, "\n")
            
            # Configure highlighting
            text_widget.tag_configure("highlight", background="yellow")
        
        # Insert recommendations
        text_widget.insert(tk.END, "RECOMMENDATIONS:\n")
        text_widget.insert(tk.END, "----------------\n")
        if detection_result["detected"]:
            text_widget.insert(tk.END, "Consider revising the following aspects to make the text more human-like:\n\n")
            
            if any(p["category"] == "Common AI Phrases" for p in detection_result["patterns"]):
                text_widget.insert(tk.END, "• Remove phrases that explicitly mention AI or limitations\n")
            
            if any(p["category"] == "Repetitive Structures" for p in detection_result["patterns"]):
                text_widget.insert(tk.END, "• Vary the structure to avoid predictable patterns\n")
            
            if any(p["category"] == "Overused Transitions" for p in detection_result["patterns"]):
                text_widget.insert(tk.END, "• Use more diverse transitional phrases\n")
            
            text_widget.insert(tk.END, "\nNote: This analysis is based on common patterns in AI-generated text ")
            text_widget.insert(tk.END, "and may not be 100% accurate. Use your judgment when making revisions.\n")
        else:
            text_widget.insert(tk.END, "No AI patterns were detected. The text appears natural and human-like.\n")
