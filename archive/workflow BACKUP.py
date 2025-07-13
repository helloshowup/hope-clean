"""
Main Workflow Module for the Simplified Workflow.

This module orchestrates the entire workflow, from reading the CSV file to saving the final output.
"""

import logging
import os
import datetime
import asyncio
from typing import Dict, List, Any, Optional
import uuid
import json
import concurrent.futures

# Import from other modules
from .csv_processor import read_csv, extract_variables, get_output_path
from .context_builder import build_context_from_adjacent_steps, build_context_for_comparison
from .content_generator import generate_three_versions, extract_educational_content, load_content_generation_template, batch_generate_for_multiple_rows
from .content_comparator import compare_and_combine
from .content_reviewer import review_content
from .ai_detector import detect_ai_patterns, edit_content
# Import batch persistence functions
from showup_core.batch_processor import (
    save_batch_state, process_existing_results,
    find_batch_for_modules_lessons, get_batch_processor
)
from .output_manager import save_as_markdown, create_output_directory, save_generation_summary, save_workflow_log

# Set up logger
logger = logging.getLogger("simplified_workflow")

def setup_logging(log_level=logging.INFO):
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (default: INFO)
    """
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Create file handler
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join("logs", f"simplified_workflow_{timestamp}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure simplified_workflow logger
    workflow_logger = logging.getLogger("simplified_workflow")
    workflow_logger.setLevel(log_level)
    
    logger.info(f"Logging configured. Log file: {log_file}")
    return log_file

async def process_row_for_phase(row_data_item: Dict[str, Any], phase: str, csv_rows: List[Dict[str, str]], 
                              output_dir: str, learner_profile: str, instance_id: str, ui_settings: Dict[str, Any]):
    """
    Process a single row for a specific workflow phase.
    
    Args:
        row_data_item: Dictionary containing row data and metadata
        phase: The phase to process ("generate", "compare", "review", "finalize")
        csv_rows: List of all rows from the CSV file
        output_dir: Directory to save output files
        learner_profile: Description of the target learner
        instance_id: Instance identifier for managing event loops
        ui_settings: Dictionary with UI settings
        
    Returns:
        Updated row_data_item with phase-specific results
    """
    try:
        # Extract common data
        row_index = row_data_item["row_index"]
        row = row_data_item["row"]
        result = row_data_item["result"]
        add_log_entry = row_data_item["add_log_entry"]
        step_info = f"Module {row.get('Module', '')}, Lesson {row.get('Lesson', '')}, Step {row.get('Step number', '')}"
        
        # Phase-specific directories
        generation_dir = os.path.join(output_dir, "generation_results")
        comparison_dir = os.path.join(output_dir, "comparison_results")
        review_dir = os.path.join(output_dir, "review_results")
        final_dir = os.path.join(output_dir, "final_content")
        
        logger.info(f"Processing {step_info} for phase: {phase}")
        
        if phase == "generate":
            # Content Generation Phase
            # Generate three versions
            add_log_entry("Generate Content", "started", "Generating three content versions")
            variables = row_data_item["variables"]
            template = row_data_item["template"]
            
            try:
                # Directly await the generation
                generations = await generate_three_versions(variables, template, instance_id=instance_id)
                add_log_entry("Generate Content", "completed", f"Generated {len(generations)} content versions")
                row_data_item["generations"] = generations
                
                # Extract educational content from each generation
                add_log_entry("Extract Content", "started", "Extracting educational content from generations")
                extracted_generations = [extract_educational_content(gen) for gen in generations]
                add_log_entry("Extract Content", "completed", "Educational content extracted successfully")
                row_data_item["extracted_generations"] = extracted_generations
                
                # Save generation results to file
                try:
                    os.makedirs(generation_dir, exist_ok=True)
                    output_file = os.path.join(generation_dir, f"{step_info.replace(',', '').replace(' ', '_')}.json")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "module": row.get("Module", ""),
                            "lesson": row.get("Lesson", ""),
                            "step_number": row.get("Step number", ""),
                            "step_title": row.get("Step title", ""),
                            "generations": generations,
                            "extracted_generations": extracted_generations
                        }, f, indent=2)
                    logger.info(f"Saved generation results to {output_file}")
                except Exception as save_e:
                    logger.error(f"Error saving generation results: {str(save_e)}")
                
            except Exception as gen_e:
                logger.error(f"Error in content generation for {step_info}: {str(gen_e)}")
                logger.exception("Exception details:")
                add_log_entry("Generate Content", "error", str(gen_e))
                row_data_item["error"] = str(gen_e)
                # Update result status
                result["status"] = "error"
                result["error"] = str(gen_e)
                result["completion_timestamp"] = datetime.datetime.now().isoformat()
            
        elif phase == "compare":
            # Content Comparison Phase
            # Verify we have generations from previous phase
            if "extracted_generations" not in row_data_item:
                error_msg = f"Missing extracted_generations for {step_info}. Cannot proceed with comparison."
                logger.error(error_msg)
                add_log_entry("Compare and Combine", "error", error_msg)
                row_data_item["error"] = error_msg
                # Update result status
                result["status"] = "error"
                result["error"] = error_msg
                result["completion_timestamp"] = datetime.datetime.now().isoformat()
                return row_data_item
            
            # Compare and combine content
            add_log_entry("Compare and Combine", "started", "Comparing and combining content versions")
            extracted_generations = row_data_item["extracted_generations"]
            comparison_context = build_context_for_comparison(csv_rows, row_index)
            comparison_context["TARGET_LEARNER"] = learner_profile
            
            try:
                # Directly await the comparison
                best_version, explanation = await compare_and_combine(
                    extracted_generations, 
                    learner_profile, 
                    comparison_context, 
                    instance_id=instance_id
                )
                
                add_log_entry("Compare and Combine", "completed", "Content versions compared and combined successfully")
                result["comparison_explanation"] = explanation
                row_data_item["best_version"] = best_version
                
                # Save comparison results to file
                try:
                    os.makedirs(comparison_dir, exist_ok=True)
                    output_file = os.path.join(comparison_dir, f"{step_info.replace(',', '').replace(' ', '_')}.json")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "module": row.get("Module", ""),
                            "lesson": row.get("Lesson", ""),
                            "step_number": row.get("Step number", ""),
                            "step_title": row.get("Step title", ""),
                            "best_version": best_version,
                            "explanation": explanation
                        }, f, indent=2)
                    logger.info(f"Saved comparison results to {output_file}")
                except Exception as save_e:
                    logger.error(f"Error saving comparison results: {str(save_e)}")
                
            except Exception as comp_e:
                logger.error(f"Error in content comparison for {step_info}: {str(comp_e)}")
                logger.exception("Exception details:")
                add_log_entry("Compare and Combine", "error", str(comp_e))
                row_data_item["error"] = str(comp_e)
                # Update result status
                result["status"] = "error"
                result["error"] = str(comp_e)
                result["completion_timestamp"] = datetime.datetime.now().isoformat()
                
                # Use first generation as fallback if comparison fails
                if "generations" in row_data_item and row_data_item["generations"]:
                    row_data_item["best_version"] = extract_educational_content(row_data_item["generations"][0])
                    result["comparison_explanation"] = f"Error in comparison. Using first version as fallback. Error: {str(comp_e)}"
            
        elif phase == "review":
            # Content Review Phase
            # Verify we have a best version from previous phase
            if "best_version" not in row_data_item:
                error_msg = f"Missing best_version for {step_info}. Cannot proceed with review."
                logger.error(error_msg)
                add_log_entry("Review Content", "error", error_msg)
                row_data_item["error"] = error_msg
                # Update result status
                result["status"] = "error"
                result["error"] = error_msg
                result["completion_timestamp"] = datetime.datetime.now().isoformat()
                
                # Try to recover using first generation if available
                if "generations" in row_data_item and row_data_item["generations"]:
                    row_data_item["best_version"] = extract_educational_content(row_data_item["generations"][0])
                    logger.info(f"Using first generation as fallback for {step_info}")
                else:
                    return row_data_item
            
            # Review content
            add_log_entry("Review Content", "started", "Reviewing content for target learner")
            best_version = row_data_item["best_version"]
            
            try:
                # Directly await the review
                reviewed_content, edit_summary = await review_content(
                    best_version, 
                    learner_profile, 
                    instance_id=instance_id
                )
                
                add_log_entry("Review Content", "completed", "Content reviewed successfully")
                result["review_summary"] = edit_summary
                row_data_item["reviewed_content"] = reviewed_content
                
                # Save review results to file
                try:
                    os.makedirs(review_dir, exist_ok=True)
                    output_file = os.path.join(review_dir, f"{step_info.replace(',', '').replace(' ', '_')}.json")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "module": row.get("Module", ""),
                            "lesson": row.get("Lesson", ""),
                            "step_number": row.get("Step number", ""),
                            "step_title": row.get("Step title", ""),
                            "reviewed_content": reviewed_content,
                            "edit_summary": edit_summary
                        }, f, indent=2)
                    logger.info(f"Saved review results to {output_file}")
                except Exception as save_e:
                    logger.error(f"Error saving review results: {str(save_e)}")
                
            except Exception as review_e:
                logger.error(f"Error in content review for {step_info}: {str(review_e)}")
                logger.exception("Exception details:")
                add_log_entry("Review Content", "error", str(review_e))
                row_data_item["error"] = str(review_e)
                # Update result status
                result["status"] = "error"
                result["error"] = str(review_e)
                result["completion_timestamp"] = datetime.datetime.now().isoformat()
                
                # Use best version as fallback if review fails
                row_data_item["reviewed_content"] = best_version
                result["review_summary"] = f"Error in review. Using best version as fallback. Error: {str(review_e)}"
            
        elif phase == "finalize":
            # Content Finalization Phase (AI Detection, Editing, and Saving)
            # Verify we have reviewed content from previous phase
            if "reviewed_content" not in row_data_item:
                error_msg = f"Missing reviewed_content for {step_info}. Cannot proceed with finalization."
                logger.error(error_msg)
                add_log_entry("Finalize Content", "error", error_msg)
                row_data_item["error"] = error_msg
                # Update result status
                result["status"] = "error"
                result["error"] = error_msg
                result["completion_timestamp"] = datetime.datetime.now().isoformat()
                
                # Try to recover using best version if available
                if "best_version" in row_data_item:
                    row_data_item["reviewed_content"] = row_data_item["best_version"]
                    logger.info(f"Using best version as fallback for {step_info}")
                else:
                    return row_data_item
            
            reviewed_content = row_data_item["reviewed_content"]
            
            # Detect AI patterns and edit content asynchronously using threadpool
            add_log_entry("Detect AI Patterns", "started", "Detecting AI patterns in content")
            try:
                # Use threadpool for potentially CPU-intensive operations
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    # Run AI detection in thread
                    detected_patterns_future = asyncio.get_event_loop().run_in_executor(
                        pool, detect_ai_patterns, reviewed_content
                    )
                    
                    # Await the detection result
                    detected_patterns = await detected_patterns_future
                    
                    add_log_entry("Detect AI Patterns", "completed", 
                                f"Detected {detected_patterns.get('count', 0)} AI patterns")
                    result["ai_patterns_detected"] = detected_patterns.get("count", 0)
                    
                    # Run editing in thread
                    add_log_entry("Edit Content", "started", "Editing content to make it more human-like")
                    edit_future = asyncio.get_event_loop().run_in_executor(
                        pool, edit_content, reviewed_content, detected_patterns, learner_profile
                    )
                    
                    # Await the editing result
                    final_content, editing_explanation = await edit_future
                    
                    add_log_entry("Edit Content", "completed", "Content edited successfully")
                    result["editing_explanation"] = editing_explanation
                    row_data_item["final_content"] = final_content
                
                # Save as markdown
                add_log_entry("Save Output", "started", "Saving content as markdown")
                output_path = get_output_path(row, output_dir)
                metadata = {
                    "module": row.get("Module", ""),
                    "lesson": row.get("Lesson", ""),
                    "step_number": row.get("Step number", ""),
                    "step_title": row.get("Step title", ""),
                    "template_type": row.get("Template Type", ""),
                    "target_learner": learner_profile
                }
                saved_path = save_as_markdown(final_content, metadata, output_path)
                add_log_entry("Save Output", "completed", f"Content saved to {saved_path}")
                result["output_path"] = saved_path
                
                # Save final results to JSON
                try:
                    os.makedirs(final_dir, exist_ok=True)
                    output_file = os.path.join(final_dir, f"{step_info.replace(',', '').replace(' ', '_')}.json")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "module": row.get("Module", ""),
                            "lesson": row.get("Lesson", ""),
                            "step_number": row.get("Step number", ""),
                            "step_title": row.get("Step title", ""),
                            "final_content": final_content,
                            "editing_explanation": editing_explanation,
                            "ai_patterns_detected": detected_patterns.get("count", 0),
                            "output_path": saved_path
                        }, f, indent=2)
                    logger.info(f"Saved final results to {output_file}")
                except Exception as save_e:
                    logger.error(f"Error saving final results: {str(save_e)}")
                
                # Update result status
                result["status"] = "completed"
                result["completion_timestamp"] = datetime.datetime.now().isoformat()
                
            except Exception as finalize_e:
                logger.error(f"Error in content finalization for {step_info}: {str(finalize_e)}")
                logger.exception("Exception details:")
                add_log_entry("Finalize Content", "error", str(finalize_e))
                row_data_item["error"] = str(finalize_e)
                
                # Update result status
                result["status"] = "error"
                result["error"] = str(finalize_e)
                result["completion_timestamp"] = datetime.datetime.now().isoformat()
        
        logger.info(f"Completed phase {phase} for {step_info}")
        return row_data_item
        
    except Exception as e:
        # Handle any unexpected errors in phase processing
        logger.error(f"Unexpected error processing phase {phase} for row {row_data_item['row_index']}: {str(e)}")
        logger.exception("Exception details:")
        
        # Update result with error
        if "result" in row_data_item:
            row_data_item["result"]["status"] = "error"
            row_data_item["result"]["error"] = str(e)
            row_data_item["result"]["completion_timestamp"] = datetime.datetime.now().isoformat()
            
            # Add error log entry if add_log_entry function is available
            if "add_log_entry" in row_data_item:
                row_data_item["add_log_entry"]("Error", "error", str(e))
        
        # Store the error in row_data_item for reference
        row_data_item["error"] = str(e)
        
        return row_data_item

async def main(csv_path: str,
              course_name: str,
              learner_profile: str,
              ui_settings: Optional[Dict[str, Any]] = None,
              selected_modules: Optional[List[str]] = None,
              instance_id: str = "default",
              workflow_phase: Optional[str] = None) -> Dict[str, Any]:
    """
    Main workflow function.
    
    Args:
        csv_path: Path to the CSV file
        course_name: Name of the course
        learner_profile: Description of the target learner
        ui_settings: Dictionary with UI settings
        selected_modules: Optional list of module names to process (if None, process all)
        instance_id: Instance identifier for managing event loops
        workflow_phase: Optional phase to execute (options: "generate", "compare", "review", "finalize", or None for all phases)
        
    Returns:
        Dictionary with summary of processed items
    """
    # Set up logging
    log_file = setup_logging()
    
    logger.info(f"Starting simplified workflow for course: {course_name}")
    logger.info(f"CSV file: {csv_path}")
    
    if selected_modules:
        logger.info(f"Processing selected modules: {', '.join(selected_modules)}")
    else:
        logger.info("Processing all modules")
    
    # Initialize UI settings if not provided
    if ui_settings is None:
        ui_settings = {}
    
    # Define the workflow phases
    all_phases = ["generate", "compare", "review", "finalize"]
    
    # Determine which phases to run - more concise implementation
    if workflow_phase is None:
        phases_to_run = all_phases
    else:
        phase_index = all_phases.index(workflow_phase) if workflow_phase in all_phases else -1
        if phase_index >= 0:
            phases_to_run = all_phases[:phase_index + 1]
        else:
            phases_to_run = all_phases
            logger.warning(f"Invalid workflow phase: {workflow_phase}. Running all phases.")
    
    logger.info(f"Running workflow phases: {', '.join(phases_to_run)}")
    
    # Initialize summary
    summary = {
        "course_name": course_name,
        "csv_path": csv_path,
        "start_time": datetime.datetime.now().isoformat(),
        "status": "started",
        "processed_rows": [],
        "log_file": log_file,
        "phases_run": phases_to_run
    }
    
    try:
        # 1. Read CSV file
        logger.info("Reading CSV file")
        csv_rows = read_csv(csv_path)
        logger.info(f"Read {len(csv_rows)} rows from CSV file")
        
        # Create directories for output and intermediate results
        output_dir = create_output_directory("output", course_name)
        logger.info(f"Created output directory: {output_dir}")
        summary["output_dir"] = output_dir
        
        # Create phase-specific directories for intermediate results
        generation_dir = os.path.join(output_dir, "generation_results")
        comparison_dir = os.path.join(output_dir, "comparison_results")
        review_dir = os.path.join(output_dir, "review_results")
        final_dir = os.path.join(output_dir, "final_content")
        
        # Create all phase directories
        for phase_dir in [generation_dir, comparison_dir, review_dir, final_dir]:
            os.makedirs(phase_dir, exist_ok=True)
            logger.info(f"Created phase directory: {phase_dir}")
        
        # Update summary with phase directories - CRITICAL FOR UI
        summary["generation_dir"] = generation_dir
        summary["comparison_dir"] = comparison_dir
        summary["review_dir"] = review_dir
        summary["final_dir"] = final_dir
        
        # 2. Filter rows by selected modules if specified
        if selected_modules:
            filtered_rows = [row for row in csv_rows if row.get("Module", "") in selected_modules]
            logger.info(f"Filtered to {len(filtered_rows)} rows for selected modules")
            csv_rows = filtered_rows
            
            if not csv_rows:
                error_msg = f"No rows found for selected modules: {', '.join(selected_modules)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        # 3. Prepare row data for all rows
        logger.info("Preparing data for all rows")
        row_data = []
        
        for i, row in enumerate(csv_rows):
            step_info = f"Module {row.get('Module', '')}, Lesson {row.get('Lesson', '')}, Step {row.get('Step number', '')}"
            logger.info(f"Preparing data for row {i+1}/{len(csv_rows)}: {step_info}")
            
            # Initialize result dictionary
            result = {
                "module": row.get("Module", ""),
                "lesson": row.get("Lesson", ""),
                "step_number": row.get("Step number", ""),
                "step_title": row.get("Step title", ""),
                "template_type": row.get("Template Type", ""),
                "status": "started",
                "timestamp": datetime.datetime.now().isoformat(),
                "log_entries": []
            }
            
            # Add log entry function
            def add_log_entry(step, status, message, result=result):
                entry = {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "step": step,
                    "status": status,
                    "message": message
                }
                result["log_entries"].append(entry)
                if status == "error":
                    logger.error(f"{step} ({step_info}): {message}")
                else:
                    logger.info(f"{step} ({step_info}): {message}")
            
            try:
                # 1. Extract variables
                add_log_entry("Extract Variables", "started", f"Extracting variables for {step_info}")
                variables = extract_variables(row, course_name, learner_profile)
                # Add UI settings to variables
                variables['ui_settings'] = ui_settings
                add_log_entry("Extract Variables", "completed", "Variables extracted successfully")
                
                # 2. Build context
                add_log_entry("Build Context", "started", "Building context from adjacent steps")
                context = build_context_from_adjacent_steps(csv_rows, i)
                variables["context"] = context
                add_log_entry("Build Context", "completed", f"Context built successfully ({len(context)} characters)")
                
                # 3. Load template
                add_log_entry("Load Template", "started", "Loading content generation template")
                template = load_content_generation_template()
                add_log_entry("Load Template", "completed", "Template loaded successfully")
                
                # Store data for this row
                row_data.append({
                    "row_index": i,
                    "row": row,
                    "variables": variables,
                    "template": template,
                    "context": context,
                    "result": result,
                    "add_log_entry": add_log_entry,
                    "phases_completed": []  # Track completed phases
                })
                
            except Exception as e:
                error_msg = f"Error preparing data for {step_info}: {str(e)}"
                logger.error(error_msg)
                logger.exception("Exception details:")
                add_log_entry("Error", "error", str(e))
                result["status"] = "error"
                result["error"] = str(e)
                result["completion_timestamp"] = datetime.datetime.now().isoformat()
                
                # Add result to summary even if preparation failed
                summary["processed_rows"].append(result)
        
        # Dictionary to track results by row for efficient summary updates
        results_by_row = {}
        
        # 4. Process all rows through each phase
        logger.info(f"DIAGNOSTIC: Starting workflow with phases: {phases_to_run}")
        
        for i, phase in enumerate(phases_to_run):
            logger.info(f"=== WORKFLOW PHASE: {phase.upper()} ({i+1}/{len(phases_to_run)}) ===")
            phase_start_time = datetime.datetime.now()
            
            # Diagnostic check on phase entry
            phase_count_before = sum(1 for row in row_data if "phases_completed" in row and phase in row["phases_completed"])
            logger.info(f"DIAGNOSTIC: Before starting phase '{phase}': {phase_count_before}/{len(row_data)} rows already have this phase completed")
            
            # Track remaining phases
            remaining_phases = phases_to_run[i+1:] if i < len(phases_to_run)-1 else []
            logger.info(f"DIAGNOSTIC: Phase sequence: Current='{phase}', Remaining={remaining_phases}")
            
            # Check if we need a batch ID for this phase
            batch_id = None
            if phase == "generate":
                # Generate a batch ID for content generation
                try:
                    batch_id = f"batch_{str(uuid.uuid4())}"
                    logger.info(f"Generated new batch ID for phase {phase}: {batch_id}")
                    
                    # Save batch state for recovery
                    try:
                        logger.info(f"Saving batch state for batch {batch_id}")
                        save_batch_state(batch_id, row_data, selected_modules=selected_modules, csv_path=csv_path)
                        logger.info(f"Successfully saved batch state for batch {batch_id}")
                    except Exception as e:
                        logger.error(f"Error saving batch state: {str(e)}")
                        logger.exception("Exception details:")
                except Exception as e:
                    logger.error(f"Error generating batch ID: {str(e)}")
                    logger.exception("Exception details:")
                    # Fallback to a timestamp-based ID
                    batch_id = f"batch_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                    logger.info(f"Generated fallback batch ID: {batch_id}")
            
            # Process all rows concurrently for this phase
            try:
                # Clear diagnostic counter before processing phase
                phase_entry_count = sum(1 for row in row_data if "phases_completed" in row and phase in row["phases_completed"])
                logger.info(f"DIAGNOSTIC: Before phase {phase}: {phase_entry_count}/{len(row_data)} rows already completed this phase")
                
                if phase == "generate" and batch_id:
                    # For generate phase, use batch generation if possible
                    logger.info(f"Starting batch generation for {len(row_data)} rows with batch ID {batch_id}")
                    logger.info(f"DIAGNOSTIC: Starting batch for phase '{phase}', phases_to_run={phases_to_run}")
                    
                    try:
                        # Use batch_generate_for_multiple_rows directly
                        batch_results = await batch_generate_for_multiple_rows(row_data, instance_id=instance_id, batch_id=batch_id)
                        
                        # Process batch results
                        for i, generations in enumerate(batch_results):
                            if i < len(row_data):
                                row_data[i]["generations"] = generations
                                row_data[i]["extracted_generations"] = [extract_educational_content(gen) for gen in generations]
                                
                                # Update log entry and mark phase as completed
                                row_data[i]["add_log_entry"]("Generate Content", "completed", 
                                                           f"Generated {len(generations)} content versions via batch")
                                row_data[i]["phases_completed"].append(phase)
                                
                                # Save generation results to file
                                try:
                                    step_info = (f"Module {row_data[i]['row'].get('Module', '')}_"
                                                f"Lesson {row_data[i]['row'].get('Lesson', '')}_"
                                                f"Step {row_data[i]['row'].get('Step number', '')}")
                                    output_file = os.path.join(generation_dir, f"{step_info}.json")
                                    with open(output_file, 'w', encoding='utf-8') as f:
                                        json.dump({
                                            "module": row_data[i]["row"].get("Module", ""),
                                            "lesson": row_data[i]["row"].get("Lesson", ""),
                                            "step_number": row_data[i]["row"].get("Step number", ""),
                                            "step_title": row_data[i]["row"].get("Step title", ""),
                                            "generations": generations,
                                            "extracted_generations": row_data[i]["extracted_generations"]
                                        }, f, indent=2)
                                    logger.info(f"Saved batch generation results to {output_file}")
                                except Exception as save_e:
                                    logger.error(f"Error saving batch generation results: {str(save_e)}")
                                
                                # Log the success
                                logger.info(f"Processed batch generation result for row {i+1}/{len(row_data)}")
                            else:
                                logger.warning(f"Received more batch results ({len(batch_results)}) than rows ({len(row_data)})")
                        
                        logger.info(f"Successfully processed batch generation for {len(batch_results)} rows")
                        
                        # Add signal that batch processing is complete
                        logger.info(f"DIAGNOSTIC: Adding phase '{phase}' to phases_completed for each row")
                        phase_completion_count = 0
                        for row in row_data:
                            if "phases_completed" in row:
                                if phase not in row["phases_completed"]:
                                    row["phases_completed"].append(phase)
                                    phase_completion_count += 1
                                logger.debug(f"DIAGNOSTIC: Row phases_completed: {row['phases_completed']}")
                            else:
                                logger.warning(f"DIAGNOSTIC: Row missing phases_completed array")
                        
                        # Signal explicitly that this phase is done
                        logger.info(f"🟢 PHASE {phase.upper()} COMPLETED VIA BATCH PROCESSING (updated {phase_completion_count}/{len(row_data)} rows)")
                        logger.info(f"DIAGNOSTIC: Moving to next phase after batch processing. Current phase: {phase}, Next phases: {phases_to_run[phases_to_run.index(phase)+1:] if phase in phases_to_run and phases_to_run.index(phase) < len(phases_to_run)-1 else 'None'}")
                        
                    except Exception as batch_e:
                        logger.error(f"Error in batch generation: {str(batch_e)}")
                        logger.exception("Exception details:")
                        logger.warning("Falling back to individual processing for generate phase")
                        
                        # Fall back to individual processing
                        tasks = [process_row_for_phase(
                            row_data_item, 
                            phase, 
                            csv_rows, 
                            output_dir, 
                            learner_profile, 
                            instance_id, 
                            ui_settings
                        ) for row_data_item in row_data]
                        
                        updated_row_data = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Process results of individual processing
                        for i, result in enumerate(updated_row_data):
                            if isinstance(result, Exception):
                                logger.error(f"Error processing row {i+1}/{len(row_data)} in phase {phase}: {str(result)}")
                                if i < len(row_data):
                                    row_data[i]["error"] = str(result)
                                    row_data[i]["result"]["status"] = "error"
                                    row_data[i]["result"]["error"] = str(result)
                                    row_data[i]["result"]["completion_timestamp"] = datetime.datetime.now().isoformat()
                            else:
                                # Make sure to update the row_data
                                row_data[i] = result
                                if "error" not in result:
                                    if phase not in row_data[i]["phases_completed"]:
                                        row_data[i]["phases_completed"].append(phase)
                else:
                    # For other phases or if batch generation failed, process rows individually but concurrently
                    logger.info(f"Processing {len(row_data)} rows individually for phase {phase}")
                    
                    tasks = [process_row_for_phase(
                        row_data_item, 
                        phase, 
                        csv_rows, 
                        output_dir, 
                        learner_profile, 
                        instance_id, 
                        ui_settings
                    ) for row_data_item in row_data]
                    
                    updated_row_data = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    for i, result in enumerate(updated_row_data):
                        if isinstance(result, Exception):
                            logger.error(f"Error processing row {i+1}/{len(row_data)} in phase {phase}: {str(result)}")
                            if i < len(row_data):
                                row_data[i]["error"] = str(result)
                                row_data[i]["result"]["status"] = "error"
                                row_data[i]["result"]["error"] = str(result)
                                row_data[i]["result"]["completion_timestamp"] = datetime.datetime.now().isoformat()
                        else:
                            # Make sure to update the row_data
                            row_data[i] = result
                            if "error" not in result:
                                if phase not in row_data[i]["phases_completed"]:
                                    row_data[i]["phases_completed"].append(phase)
            
            except Exception as phase_e:
                logger.error(f"Error processing phase {phase}: {str(phase_e)}")
                logger.exception("Exception details:")
            
            # Flush the specific queue for this phase
            try:
                batch_processor = get_batch_processor(instance_id=instance_id)
                # Map phases to queue names
                queue_names = {
                    "generate": "content_generation",
                    "compare": "content_comparison",
                    "review": "content_review",
                    "finalize": None  # finalize doesn't have a specific queue
                }
                
                queue_name = queue_names.get(phase)
                if queue_name:
                    batch_processor.flush_queue(queue_name)
                    logger.info(f"Flushed {queue_name} queue after phase {phase}")
                else:
                    # If it's the finalize phase or no mapping, flush all queues as a safety measure
                    batch_processor.flush_all_queues()
                    logger.info(f"Flushed all batch queues after phase {phase}")
            except Exception as e:
                logger.warning(f"Error flushing batch queues: {str(e)}")
            # Check the completion status for this phase
            completed = sum(1 for item in row_data if phase in item.get("phases_completed", []))
            errors = sum(1 for item in row_data if phase not in item.get("phases_completed", []))
            
            # Log phase completion
            phase_duration = (datetime.datetime.now() - phase_start_time).total_seconds()
            logger.info(f"Phase {phase} completed in {phase_duration:.2f} seconds. Successful: {completed}, Errors: {errors}")
            
            # CRITICAL DIAGNOSTIC: Track phase transition
            phase_idx = phases_to_run.index(phase)
            if phase_idx < len(phases_to_run) - 1:
                next_phase = phases_to_run[phase_idx + 1]
                logger.info(f"DIAGNOSTIC: End of phase '{phase}' - Next phase to run: '{next_phase}'")
                
                # Check eligibility for next phase
                eligible_for_next = sum(1 for item in row_data if phase in item.get("phases_completed", []))
                logger.info(f"DIAGNOSTIC: {eligible_for_next}/{len(row_data)} rows eligible to proceed to next phase '{next_phase}'")
                
                for idx, item in enumerate(row_data):
                    phases = item.get("phases_completed", [])
                    logger.debug(f"DIAGNOSTIC: Row {idx+1} phases completed: {phases}")
            else:
                logger.info(f"DIAGNOSTIC: End of final phase '{phase}' - No more phases to run")
            
            
            # Update summary with phase results - more efficient approach
            summary["processed_rows"] = []
            for item in row_data:
                if "result" in item:
                    row_key = (item["result"].get("module", ""), 
                              item["result"].get("lesson", ""), 
                              item["result"].get("step_number", ""))
                    
                    # Update our tracking dictionary
                    results_by_row[row_key] = item["result"]
            
            # Add all results to the summary
            summary["processed_rows"] = list(results_by_row.values())
            
            # Save summary with just the phase results to phase-specific directory
            phase_summary = {**summary}
            phase_summary["phase"] = phase
            phase_summary["phase_completion_time"] = datetime.datetime.now().isoformat()
            phase_summary_path = os.path.join(output_dir, f"summary_{phase}.json")
            
            try:
                with open(phase_summary_path, 'w', encoding='utf-8') as f:
                    json.dump(phase_summary, f, indent=2)
                logger.info(f"Saved phase summary to {phase_summary_path}")
            except Exception as save_e:
                logger.error(f"Error saving phase summary: {str(save_e)}")
            
            # Count rows that have completed this phase
            completed_count = sum(1 for row in row_data if "phases_completed" in row and phase in row["phases_completed"])
            logger.info(f"DIAGNOSTIC: Phase {phase} completed for {completed_count}/{len(row_data)} rows")
            
            # If this was the requested phase, stop here
            if phase == workflow_phase:
                logger.info(f"Stopping after requested phase: {workflow_phase}")
                logger.info(f"DIAGNOSTIC: Early termination requested after phase: {workflow_phase}")
                break
        
        # 5. Save workflow log
        log_entries = []
        for row_result in summary["processed_rows"]:
            log_entries.extend(row_result.get("log_entries", []))
        
        log_path = save_workflow_log(output_dir, log_entries)
        summary["workflow_log"] = log_path
        
        # 6. Update summary status
        summary["status"] = "completed"
        summary["end_time"] = datetime.datetime.now().isoformat()
        summary["success_count"] = sum(1 for r in summary["processed_rows"] if r.get("status") == "completed")
        summary["error_count"] = sum(1 for r in summary["processed_rows"] if r.get("status") == "error")
        
        # Add batch status information
        summary["batch_status"] = "completed"
        
        # Collect phases completed across all rows
        all_phases_completed = set()
        for row in row_data:
            if "phases_completed" in row:
                all_phases_completed.update(row["phases_completed"])
        summary["phases_completed"] = list(all_phases_completed)
        
        # 7. Save final summary
        summary_path = save_generation_summary(output_dir, summary)
        summary["summary_path"] = summary_path
        
        logger.info(f"Workflow completed. Processed {len(csv_rows)} rows. "
                   f"Success: {summary['success_count']}, Errors: {summary['error_count']}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"🏁 WORKFLOW COMPLETED WITH PHASES: {', '.join(list(all_phases_completed))}")
        
        # Ensure the directory paths are in the summary for the UI
        if "generation_dir" not in summary:
            summary["generation_dir"] = generation_dir
        if "comparison_dir" not in summary:
            summary["comparison_dir"] = comparison_dir
        if "review_dir" not in summary:
            summary["review_dir"] = review_dir
        if "final_dir" not in summary:
            summary["final_dir"] = final_dir
        
        # Log the type of summary being returned
        logger.info(f"Returning summary of type {type(summary).__name__}: {str(summary)[:100]}...")
        return summary
        
    except Exception as e:
        error_msg = f"Error in workflow: {str(e)}"
        logger.error(error_msg)
        logger.exception("Exception details:")
        
        # Update summary status
        summary["status"] = "error"
        summary["error"] = str(e)
        summary["end_time"] = datetime.datetime.now().isoformat()
        
        # Try to save summary even if there was an error
        try:
            if "output_dir" in summary:
                summary_path = save_generation_summary(summary["output_dir"], summary)
                summary["summary_path"] = summary_path
        except Exception as save_error:
            logger.error(f"Error saving summary: {str(save_error)}")
        
        # Ensure directory paths are in the summary even in case of error
        if "output_dir" in summary:
            output_dir = summary["output_dir"]
            if "generation_dir" not in summary:
                summary["generation_dir"] = os.path.join(output_dir, "generation_results")
            if "comparison_dir" not in summary:
                summary["comparison_dir"] = os.path.join(output_dir, "comparison_results")
            if "review_dir" not in summary:
                summary["review_dir"] = os.path.join(output_dir, "review_results")
            if "final_dir" not in summary:
                summary["final_dir"] = os.path.join(output_dir, "final_content")
        
        # Log the type of summary being returned
        logger.info(f"Returning error summary of type {type(summary).__name__}: {str(summary)[:100]}...")
        return summary

def run_workflow(csv_path: str, course_name: str, learner_profile: str,
                ui_settings: Optional[Dict[str, Any]] = None,
                selected_modules: Optional[List[str]] = None,
                instance_id: str = "default",
                workflow_phase: Optional[str] = None) -> Dict[str, Any]:
    """
    Alias for main function with instance_id parameter.
    """
    try:
        # Use asyncio.run to properly await the result of the main coroutine
        result = asyncio.run(main(csv_path, course_name, learner_profile, ui_settings, selected_modules, instance_id, workflow_phase))
        
        # Ensure result is a dictionary to prevent 'coroutine' object has no attribute 'get' error
        if not isinstance(result, dict):
            logger.error(f"main() returned non-dictionary result of type {type(result).__name__}. Converting to error dictionary.")
            # Create a fallback error dictionary
            result = {
                "status": "error",
                "error": f"Workflow returned unexpected result type: {type(result).__name__}",
                "output_dir": "unknown",
                "processed_rows": [],
                "generation_dir": "unknown",
                "comparison_dir": "unknown",
                "review_dir": "unknown",
                "final_dir": "unknown"
            }
        
        # Ensure result contains all required directory paths for UI
        required_keys = ["generation_dir", "comparison_dir", "review_dir", "final_dir"]
        for key in required_keys:
            if key not in result and "output_dir" in result:
                # Add missing keys with default paths if output_dir is available
                phase_name = key.replace("_dir", "")
                result[key] = os.path.join(result["output_dir"], f"{phase_name}_results")
                logger.warning(f"Added missing {key} to workflow result for UI compatibility")
        
        return result
    except Exception as e:
        # Catch any exceptions that might occur during the execution of main
        logger.error(f"Exception in run_workflow: {str(e)}")
        logger.exception("Exception details:")
        
        # Return an error dictionary that the UI can handle
        return {
            "status": "error",
            "error": f"Workflow execution failed: {str(e)}",
            "output_dir": "unknown",
            "processed_rows": [],
            "generation_dir": "unknown",
            "comparison_dir": "unknown",
            "review_dir": "unknown",
            "final_dir": "unknown"
        }

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run simplified workflow for content generation")
    parser.add_argument("csv_path", help="Path to the CSV file")
    parser.add_argument("course_name", help="Name of the course")
    parser.add_argument("learner_profile", help="Description of the target learner")
    parser.add_argument("--modules", nargs="+", help="List of modules to process (optional)")
    parser.add_argument("--phase", choices=["generate", "compare", "review", "finalize"],
                        help="Optional workflow phase to execute (default: all phases)")
    
    args = parser.parse_args()
    
    # Run the workflow
    asyncio.run(main(args.csv_path, args.course_name, args.learner_profile,
         selected_modules=args.modules, workflow_phase=args.phase))