"""
Batch Processor Module for ShowupSquaredV3.

This module provides batch processing capabilities for Claude API calls,
using the Claude Batch API to reduce costs and improve throughput.
"""

# Event loop safety fixes:
# - Ensures each thread has its own event loop
# - Uses thread-safe methods to set future results
# - Properly handles event loop errors in the polling thread
# - Added debug mode for event loop diagnostics (set DEBUG_EVENT_LOOPS=1)

import os
# Add debug mode for event loop diagnostics
DEBUG_EVENT_LOOPS = os.environ.get("DEBUG_EVENT_LOOPS", "0") == "1"
import time
import json
import uuid
import logging
import asyncio
import threading
import datetime
import requests
from typing import Dict, List, Any, Optional

# Import batch persistence module
from .batch_persistence import (
    save_batch_state, cache_batch_results, process_existing_results,
    clean_up_old_state_files,
    clean_up_old_result_files
)

# Set up logger
logger = logging.getLogger("batch_processor")

# Dictionary of task-specific event loops
# Dictionary of event loops, keyed by instance_id and task_type
_event_loops_by_instance = {}

def get_or_create_event_loop(instance_id="default", task_type="default"):
    """
    Get a task-specific event loop for a specific instance or create a new one if it doesn't exist.
    
    Args:
        instance_id: The ID of the application instance
        task_type: The type of task (e.g., "content_generation", "content_comparison")
        
    Returns:
        asyncio.AbstractEventLoop: The task-specific event loop
    """
    global _event_loops_by_instance
    
    # Create instance dictionary if it doesn't exist
    if instance_id not in _event_loops_by_instance:
        _event_loops_by_instance[instance_id] = {}
    
    # Get the event loops for this instance
    instance_loops = _event_loops_by_instance[instance_id]
    
    # Create or get the event loop for this task type
    if task_type not in instance_loops or instance_loops[task_type].is_closed():
        try:
            # Create a new event loop for this task type
            instance_loops[task_type] = asyncio.new_event_loop()
            logger.debug(f"Created new event loop for instance {instance_id}, task type {task_type}: {id(instance_loops[task_type])}")
        except Exception as e:
            logger.error(f"Error creating event loop for instance {instance_id}, task type {task_type}: {str(e)}")
            # Fallback to current event loop
            try:
                instance_loops[task_type] = asyncio.get_event_loop()
            except RuntimeError:
                instance_loops[task_type] = asyncio.new_event_loop()
            logger.debug(f"Using existing event loop for instance {instance_id}, task type {task_type}: {id(instance_loops[task_type])}")
    
    return instance_loops[task_type]

def safely_await_future(future, timeout=None):
    """
    Safely await a future using the event loop that created it.
    
    Args:
        future: The future to await
        timeout: Optional timeout in seconds
        
    Returns:
        The result of the future
        
    Raises:
        Various exceptions that might be raised by the future itself
    """
    if not asyncio.isfuture(future):
        logger.error(f"Not a valid future: {type(future)}")
        raise ValueError("Object is not a valid future")
        
    # Get the loop that owns this future
    future_loop = future._loop
    
    # If the future is already done, just return the result
    if future.done():
        try:
            return future.result()
        except Exception as e:
            logger.error(f"Error retrieving result from completed future: {str(e)}")
            raise
    
    # Use the future's own loop to run it to completion
    logger.debug(f"Running future {id(future)} in its original loop {id(future_loop)}")
    
    # Create a simple function to await the future with optional timeout
    async def await_with_timeout():
        if timeout:
            return await asyncio.wait_for(future, timeout)
        else:
            return await future
    
    try:
        # Run the future in its own loop
        return future_loop.run_until_complete(await_with_timeout())
    except Exception as e:
        logger.error(f"Error awaiting future: {str(e)}")
        raise

class ProgressTracker:
    """
    Tracks and reports on batch processing progress.
    
    This class provides visibility into the status of batch processing,
    ensuring users can see that the system is making progress and hasn't frozen.
    """
    
    def __init__(self):
        """Initialize the progress tracker."""
        self.batch_statuses = {}
        self.logger = logging.getLogger("batch_processor.progress")
    
    def update_batch_status(self, batch_id: str, status: str, processing: int = 0, 
                           succeeded: int = 0, errored: int = 0):
        """
        Update the status of a batch.
        
        Args:
            batch_id: ID of the batch
            status: Status of the batch (submitted, in_progress, completed)
            processing: Number of requests still processing
            succeeded: Number of successful requests
            errored: Number of failed requests
        """
        # Update status
        self.batch_statuses[batch_id] = {
            "status": status,
            "processing": processing,
            "succeeded": succeeded,
            "errored": errored,
            "updated_at": datetime.datetime.now()
        }
        
        # Log status update
        self.logger.info(f"Batch {batch_id} status: {status} - Processing: {processing}, Succeeded: {succeeded}, Errored: {errored}")
        
        # Print status to console for immediate visibility
        print(f"Batch {batch_id} status: {status} - Processing: {processing}, Succeeded: {succeeded}, Errored: {errored}")
    
    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Get the status of a batch.
        
        Args:
            batch_id: ID of the batch
            
        Returns:
            Status dictionary
        """
        return self.batch_statuses.get(batch_id, {"status": "unknown"})
    
    def get_all_batch_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all batches.
        
        Returns:
            Dictionary of batch statuses
        """
        return self.batch_statuses
    
    def get_active_batches(self) -> List[str]:
        """
        Get a list of active batch IDs.
        
        Returns:
            List of batch IDs that are still processing
        """
        return [
            batch_id for batch_id, status in self.batch_statuses.items()
            if status.get("status") in ["submitted", "in_progress"]
        ]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all batch processing.
        
        Returns:
            Summary dictionary with counts of batches in different states
        """
        summary = {
            "total_batches": len(self.batch_statuses),
            "active_batches": 0,
            "completed_batches": 0,
            "failed_batches": 0,
            "total_requests": 0,
            "succeeded_requests": 0,
            "errored_requests": 0,
            "processing_requests": 0
        }
        
        for batch_id, status in self.batch_statuses.items():
            if status.get("status") in ["submitted", "in_progress"]:
                summary["active_batches"] += 1
            elif status.get("status") == "completed":
                summary["completed_batches"] += 1
            else:
                summary["failed_batches"] += 1
                
            summary["total_requests"] += status.get("processing", 0) + status.get("succeeded", 0) + status.get("errored", 0)
            summary["succeeded_requests"] += status.get("succeeded", 0)
            summary["errored_requests"] += status.get("errored", 0)
            summary["processing_requests"] += status.get("processing", 0)
            
        return summary

class ErrorHandler:
    """
    Handles failed requests by retrying them individually.
    
    This class provides error handling for batch processing,
    ensuring that failed requests are retried individually.
    """
    
    def __init__(self):
        """Initialize the error handler."""
        self.logger = logging.getLogger("batch_processor.error_handler")
        self.results = {}  # Store results from retries
    
    def retry_request(self, request: Dict[str, Any]):
            """
            This method is kept for backward compatibility but now raises an error
            instead of retrying requests individually.
            
            Args:
                request: Failed request object
            """
            request_id = request.get('custom_id', 'unknown')
            self.logger.error(f"BATCH PROCESSING REQUIRED: Individual retries are disabled for request {request_id}")
            
            # Log detailed information about the request
            self.logger.error(f"Request details: model={request.get('model', 'unknown')}, task_type={request.get('task_type', 'unknown')}")
            
            # Create an error message
            error_msg = "Individual request retries have been disabled. Batch processing is required."
            
            # Set the exception on the future if possible
            try:
                if "future" in request and request["future"] is not None:
                    if "loop" in request and request["loop"] is not None:
                        loop = request["loop"]
                        if asyncio.isfuture(request["future"]) and request["future"]._loop == loop:
                            request["future"].set_exception(RuntimeError(f"BATCH PROCESSING REQUIRED: {error_msg}"))
                            self.logger.debug(f"Set exception on future for request {request_id}")
            except Exception as ex:
                self.logger.warning(f"Could not set exception on future for request {request_id}: {str(ex)}")
            
            # Raise an exception
            raise RuntimeError(f"BATCH PROCESSING REQUIRED: {error_msg}")
    
    def _handle_retry_response(self, request, content, error):
        """Handle response from retry without using the future."""
        request_id = request.get('custom_id', 'unknown')
        
        # Initialize results dictionary if it doesn't exist
        if not hasattr(self, 'results'):
            self.results = {}
        
        if error:
            self.logger.error(f"Retry failed for request {request_id}: {error}")
            # Store the error in a results dictionary instead of using futures
            self.results[request_id] = {"status": "error", "error": str(error)}
            
            # Try to safely set the exception on the future if possible
            try:
                if "future" in request and request["future"] is not None:
                    if "loop" in request and request["loop"] is not None:
                        loop = request["loop"]
                        if asyncio.isfuture(request["future"]) and request["future"]._loop == loop:
                            request["future"].set_exception(error)
                            self.logger.debug(f"Successfully set exception on future for request {request_id}")
                        else:
                            self.logger.warning(f"Future for request {request_id} belongs to a different loop, not setting exception")
            except Exception as ex:
                self.logger.warning(f"Could not set exception on future for request {request_id}: {str(ex)}")
        else:
            self.logger.info(f"Successfully retried request {request_id}")
            # Store the result in a results dictionary instead of using futures
            self.results[request_id] = {"status": "success", "content": content}
            
            # Try to safely set the result on the future if possible
            try:
                if "future" in request and request["future"] is not None:
                    future = request["future"]
                    if asyncio.isfuture(future):
                        future_loop = future._loop
                        current_loop = asyncio.get_event_loop()
                        
                        if future_loop == current_loop:
                            # Same loop - direct set_result is safe
                            future.set_result(content)
                            self.logger.debug(f"Successfully set result on future for request {request_id}")
                        else:
                            # Different loop - use call_soon_threadsafe to safely set result
                            self.logger.info(f"Setting result on future from different loop for request {request_id}: future_loop={id(future_loop)}, current_loop={id(current_loop)}")
                            def set_result_callback():
                                if not future.done():
                                    future.set_result(content)
                            future_loop.call_soon_threadsafe(set_result_callback)
                            self.logger.debug(f"Successfully scheduled result setting on future for request {request_id}")
                    else:
                        self.logger.warning(f"Object for request {request_id} is not a valid future: {type(future)}")
            except Exception as ex:
                self.logger.warning(f"Could not set result on future for request {request_id}: {str(ex)}")


class BatchManager:
    """
    Manages batch creation, submission, and polling.
    
    This class is responsible for creating batches, submitting them to the
    Claude Batch API, and polling for results.
    """
    
    def __init__(self, max_batch_size: int = 100, polling_interval: int = 10):
        """
        Initialize the batch manager.
        
        Args:
            max_batch_size: Maximum number of items in a batch
            polling_interval: Seconds between polling for batch results
        """
        self.max_batch_size = max_batch_size
        self.polling_interval = polling_interval
        self.active_batches = {}  # Keyed by batch ID
        self.progress_tracker = ProgressTracker()
        self.error_handler = ErrorHandler()
        self.logger = logging.getLogger("batch_processor.manager")
        
    def submit_batch(self, requests: List[Dict[str, Any]], task_type: str):
        """
        Submit a batch of requests to the Claude Batch API.
        
        Args:
            requests: List of request objects
            task_type: Type of task
        """
        # Log batch submission with detailed information
        self.logger.info(f"Submitting batch of {len(requests)} requests for task type: {task_type} (max_batch_size={self.max_batch_size})")
        
        # Add detailed logging for batch size and timeout settings
        self.logger.info(f"Batch size: {len(requests)} requests, Submission timeout: 180 seconds")
        
        # Log warning if batch size is large
        if len(requests) > 50:
            self.logger.warning(f"Large batch size detected: {len(requests)} requests. This may increase the risk of timeout errors.")
        
        # Prepare the batch request
        batch_requests = []
        for request in requests:
            # Create request parameters with system prompt as a top-level parameter
            # and user prompt in the messages array
            params = {
                "model": request["model"],
                "max_tokens": request["max_tokens"],
                "temperature": request["temperature"],
                "messages": [{"role": "user", "content": request["prompt"]}]
            }
            
            # Add system prompt as a top-level parameter if available
            if request["system_prompt"]:
                params["system"] = request["system_prompt"]
            
            batch_requests.append({
                "custom_id": request["custom_id"],
                "params": params
            })
        
        # Log batch request format for debugging
        if batch_requests:
            self.logger.info(f"Submitting batch with {len(batch_requests)} requests")
            try:
                import json
                self.logger.debug(f"Batch request format sample: {json.dumps(batch_requests[0], indent=2)}")
            except Exception as e:
                self.logger.warning(f"Could not log batch request format: {str(e)}")
        
        try:
            # Check if we have an existing batch for these requests
            existing_batch_id = self._check_for_existing_batch(requests, task_type)
            
            if existing_batch_id:
                self.logger.info(f"Found existing batch {existing_batch_id} for task type {task_type}")
                
                # Check if we have existing results for this batch
                existing_results = process_existing_results(existing_batch_id)
                
                if existing_results:
                    self.logger.info(f"Found {len(existing_results)} existing results for batch {existing_batch_id}")
                    
                    # Process the existing results
                    self._process_existing_results(requests, existing_results)
                    
                    # Return early, no need to submit a new batch
                    return
                else:
                    self.logger.info(f"No existing results found for batch {existing_batch_id}, submitting new batch")
            
            # Submit the batch
            batch_id = self._submit_to_claude_batch_api(batch_requests)
            
            # Save batch state for recovery
            self._save_batch_state(batch_id, requests, task_type)
            
            # Store the batch
            self.active_batches[batch_id] = {
                "requests": requests,
                "task_type": task_type,
                "status": "in_progress",
                "submitted_at": datetime.datetime.now()
            }
            
            # Start polling for results
            self._start_polling(batch_id)
            
            # Update progress tracker
            self.progress_tracker.update_batch_status(batch_id, "submitted", len(requests))
            
            self.logger.info(f"Successfully submitted batch {batch_id} with {len(requests)} requests")
        except Exception as e:
            self.logger.error(f"Error submitting batch: {str(e)}")
            
            # Log detailed error information
            self.logger.error(f"BATCH PROCESSING REQUIRED: Batch submission failed with error: {str(e)}")
            
            # Raise an exception instead of falling back to individual processing
            raise RuntimeError(f"BATCH PROCESSING REQUIRED: Batch submission failed: {str(e)}")
    
    def _check_for_existing_batch(self, requests: List[Dict[str, Any]], task_type: str) -> Optional[str]:
        """
        Check if we have an existing batch for these requests.
        
        Args:
            requests: List of request objects
            task_type: Type of task
            
        Returns:
            Batch ID if found, None otherwise
        """
        # This is a simplified implementation that just checks if we have
        # a batch with the same number of requests and task type
        # A more sophisticated implementation would check the actual content
        # of the requests to see if they match
        
        # For now, we'll just return None to always create a new batch
        return None
    
    def _save_batch_state(self, batch_id: str, requests: List[Dict[str, Any]], task_type: str):
        """
        Save batch state for recovery.
        
        Args:
            batch_id: ID of the batch
            requests: List of request objects
            task_type: Type of task
        """
        try:
            # Extract row data from requests
            # This is a simplified implementation that assumes all requests
            # have the same structure
            row_data_list = []
            
            # Save batch state
            save_batch_state(batch_id, row_data_list)
            
            self.logger.info(f"Saved state for batch {batch_id} with {len(requests)} requests")
        except Exception as e:
            self.logger.error(f"Error saving batch state: {str(e)}")
            self.logger.exception("Exception details:")
    
    def _process_existing_results(self, requests: List[Dict[str, Any]], existing_results: Dict[str, str]):
        """
        Process existing results for requests.
        
        Args:
            requests: List of request objects
            existing_results: Dictionary mapping custom IDs to content
        """
        self.logger.info(f"Processing {len(existing_results)} existing results for {len(requests)} requests")
        
        # Process each request
        for request in requests:
            custom_id = request.get("custom_id")
            
            if custom_id in existing_results:
                content = existing_results[custom_id]
                
                # Set the future result
                try:
                    if "future" in request and request["future"] is not None:
                        # Safely set result using the future's original event loop
                        future = request["future"]
                        future_loop = future._loop
                        current_loop = asyncio.get_event_loop()
                        
                        if future_loop == current_loop:
                            # Same loop - direct set_result is safe
                            future.set_result(content)
                        else:
                            # Different loop - use call_soon_threadsafe
                            self.logger.info(f"Setting result on future from different loop: future_loop={id(future_loop)}, current_loop={id(current_loop)}")
                            def set_result_callback():
                                if not future.done():
                                    future.set_result(content)
                            future_loop.call_soon_threadsafe(set_result_callback)
                        
                        self.logger.info(f"Set result from existing results for request {custom_id}")
                except Exception as e:
                    self.logger.error(f"Error setting result from existing results for request {custom_id}: {str(e)}")
            else:
                self.logger.warning(f"No existing result found for request {custom_id}")
                
                # Set an exception on the future
                try:
                    if "future" in request and request["future"] is not None:
                        future = request["future"]
                        future_loop = future._loop
                        current_loop = asyncio.get_event_loop()
                        
                        error = Exception(f"No existing result found for request {custom_id}")
                        
                        if future_loop == current_loop:
                            # Same loop - direct set_exception is safe
                            future.set_exception(error)
                        else:
                            # Different loop - use call_soon_threadsafe
                            self.logger.info(f"Setting exception on future from different loop for request {custom_id}: future_loop={id(future_loop)}, current_loop={id(current_loop)}")
                            def set_exception_callback():
                                if not future.done():
                                    future.set_exception(error)
                            future_loop.call_soon_threadsafe(set_exception_callback)
                            self.logger.debug(f"Successfully scheduled exception setting for request {custom_id}")
                except Exception as e:
                    self.logger.error(f"Error setting exception for request {custom_id}: {str(e)}")
    
    def _submit_to_claude_batch_api(self, batch_requests: List[Dict[str, Any]]) -> str:
        """
        Submit a batch to the Claude Batch API.
        
        Args:
            batch_requests: List of request objects formatted for the Batch API
            
        Returns:
            Batch ID
        """
        # Get API key from environment or config
        api_key = None
        
        # Try to get from environment variables with dotenv
        try:
            # Add debug logging
            self.logger.info("Attempting to load environment variables from .env file")
            
            # Import dotenv
            from dotenv import load_dotenv
            
            # Get current working directory for debugging
            import os as dotenv_os  # Use a different name to avoid scope issues
            current_dir = dotenv_os.getcwd()
            self.logger.info(f"Current working directory: {current_dir}")
            
            # Try to load from the ShowupSquared directory .env file
            dotenv_path = dotenv_os.path.join(dotenv_os.path.dirname(dotenv_os.path.dirname(dotenv_os.path.abspath(__file__))), '.env')
            self.logger.info(f"Looking for .env file at: {dotenv_path}")
            self.logger.info(f"Dotenv file exists: {dotenv_os.path.exists(dotenv_path)}")
            
            # Load the .env file
            load_dotenv(dotenv_path)
            self.logger.info("Successfully loaded .env file")
            
            # Get the API key
            api_key = dotenv_os.getenv("ANTHROPIC_API_KEY")
            self.logger.info(f"ANTHROPIC_API_KEY exists: {api_key is not None}")
            if api_key:
                self.logger.info("Using Claude API key from environment variables for batch processing")
        except ImportError:
            self.logger.warning("Could not import dotenv, falling back to config")
        except Exception as e:
            self.logger.warning(f"Error loading from .env: {str(e)}")
            self.logger.exception("Exception details:")
        
        # If not found in environment, try config file
        if not api_key:
            try:
                from config.api_keys import ANTHROPIC_API_KEY
                api_key = ANTHROPIC_API_KEY
                if api_key:
                    self.logger.info("Using Claude API key from config file for batch processing")
            except ImportError:
                self.logger.error("Could not import ANTHROPIC_API_KEY from config.api_keys")
        
        # Check if we have an API key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or config")
        
        # Prepare headers
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": api_key
        }
        
        # Prepare data
        data = {
            "requests": batch_requests
        }
        
        # Log the complete request payload (excluding API key)
        log_headers = headers.copy()
        log_headers["x-api-key"] = "********"  # Mask the API key in logs
        
        self.logger.info(f"Submitting batch with {len(batch_requests)} requests")
        self.logger.info(f"Using 180-second timeout for batch submission of {len(batch_requests)} requests")
        self.logger.debug(f"Batch request headers: {json.dumps(log_headers, indent=2)}")
        self.logger.debug(f"Batch request payload: {json.dumps(data, indent=2)}")
        
        # Save the complete batch request to a file for inspection
        try:
            import os
            import datetime
            
            # Create logs directory if it doesn't exist
            log_dir = "C:/Users/User/Desktop/ShowupSquaredV4/logs"
            os.makedirs(log_dir, exist_ok=True)
            
            # Generate timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create file paths
            batch_request_file = os.path.join(log_dir, f"batch_request_{timestamp}.txt")
            
            # Save batch request to file
            with open(batch_request_file, 'w', encoding='utf-8') as f:
                # Save the full JSON data
                f.write(json.dumps(data, indent=2))
                
                # Also save a more readable version of each prompt
                f.write("\n\n=== INDIVIDUAL PROMPTS ===\n\n")
                for i, request in enumerate(batch_requests):
                    f.write(f"\n--- REQUEST {i+1} (ID: {request['custom_id']}) ---\n\n")
                    f.write(f"Model: {request['params']['model']}\n")
                    f.write(f"Temperature: {request['params']['temperature']}\n")
                    f.write(f"Max Tokens: {request['params']['max_tokens']}\n")
                    
                    # Extract system prompt if present
                    if 'system' in request['params']:
                        f.write(f"\nSYSTEM PROMPT:\n{request['params']['system']}\n")
                    
                    # Extract user prompt
                    if 'messages' in request['params'] and len(request['params']['messages']) > 0:
                        user_message = request['params']['messages'][0]
                        if user_message['role'] == 'user' and 'content' in user_message:
                            f.write(f"\nUSER PROMPT:\n{user_message['content']}\n")
            
            self.logger.info(f"Saved complete batch request to: {batch_request_file}")
            print(f"BATCH REQUEST SAVED: {batch_request_file}")
        except Exception as e:
            self.logger.error(f"Error saving batch request to file: {str(e)}")
        
        try:
            # Submit batch
            # Increase timeout for batch submission to handle large batches
            # The original 30-second timeout was too short for batches of ~100 requests
            response = requests.post(
                "https://api.anthropic.com/v1/messages/batches",
                headers=headers,
                json=data,
                timeout=180  # 3-minute timeout for batch submission
            )
            
            # Log the complete response
            self.logger.debug(f"Batch submission response status: {response.status_code}")
            self.logger.debug(f"Batch submission response: {response.text}")
            
            # Save the batch response to a file for inspection
            try:
                import os
                import datetime
                
                # Create logs directory if it doesn't exist
                log_dir = "C:/Users/User/Desktop/ShowupSquaredV4/logs"
                os.makedirs(log_dir, exist_ok=True)
                
                # Generate timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Create file path
                batch_response_file = os.path.join(log_dir, f"batch_response_{timestamp}.txt")
                
                # Save batch response to file
                with open(batch_response_file, 'w', encoding='utf-8') as f:
                    # Save the raw response
                    f.write(response.text)
                    
                    # Try to parse and save a more readable version
                    try:
                        response_json = response.json()
                        f.write("\n\n=== PARSED RESPONSE ===\n\n")
                        f.write(json.dumps(response_json, indent=2))
                    except:
                        f.write("\n\n=== COULD NOT PARSE RESPONSE AS JSON ===\n")
                
                self.logger.info(f"Saved batch response to: {batch_response_file}")
                print(f"BATCH RESPONSE SAVED: {batch_response_file}")
            except Exception as e:
                self.logger.error(f"Error saving batch response to file: {str(e)}")
            
            # Check for errors
            response.raise_for_status()
            result = response.json()
            
            # Return batch ID
            self.logger.info(f"Successfully submitted batch with ID: {result['id']}")
            return result["id"]
        except requests.exceptions.RequestException as e:
            # Log detailed error information
            error_detail = ""
            if hasattr(e, 'response') and e.response:
                try:
                    error_detail = e.response.json()
                    self.logger.error(f"Batch submission error details: {json.dumps(error_detail, indent=2)}")
                except:
                    error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
                    self.logger.error(f"Batch submission error: {error_detail}")
            else:
                self.logger.error(f"Batch submission error: {str(e)}")
            
            # Re-raise the exception
            raise
    
    def _start_polling(self, batch_id: str):
        """
        Start polling for batch results.
        
        Args:
            batch_id: ID of the batch to poll for
        """
        # Start a background thread to poll for results
        polling_thread = threading.Thread(
            target=self._poll_for_results, 
            args=(batch_id,),
            daemon=True  # Make thread a daemon so it doesn't block program exit
        )
        polling_thread.start()
    
    def _poll_for_results(self, batch_id: str):
        """
        Poll for batch results.
        
        Args:
            batch_id: ID of the batch to poll for
        """
        thread_id = threading.get_ident()
        
        try:
            # Set up thread-specific logging
            logger.info(f"Starting poll_for_results thread {thread_id}")
            
            # Ensure this thread has its own event loop
            try:
                loop = asyncio.get_event_loop()
                logger.info(f"Thread {thread_id} already has event loop: {id(loop)}")
                if DEBUG_EVENT_LOOPS:
                    logger.info(f"Event loop info in _poll_for_results - Thread {thread_id}: "
                               f"loop={id(loop)}, running={loop.is_running()}")
            except RuntimeError:
                logger.info(f"Thread {thread_id} has no event loop, creating one")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info(f"Created and set new event loop {id(loop)} for thread {thread_id}")
                if DEBUG_EVENT_LOOPS:
                    logger.info(f"New event loop created in _poll_for_results - Thread {thread_id}: "
                               f"loop={id(loop)}, running={loop.is_running()}")

            # Define max_retries before using it
            max_retries = 720  # Allow for up to 2 hours of polling (720 * 10 seconds = 7200 seconds = 2 hours)
            self.logger.info(f"Starting to poll for batch {batch_id} results (max_retries={max_retries}, polling_interval={self.polling_interval})")
            
            # Get API key
            try:
                # Use a different name for os to avoid scope issues
                import os as poll_os
                api_key = poll_os.getenv("ANTHROPIC_API_KEY")
                self.logger.info(f"In _poll_for_results: ANTHROPIC_API_KEY exists: {api_key is not None}")
                if not api_key:
                    self.logger.error("ANTHROPIC_API_KEY environment variable not set")
                    return
            except Exception as e:
                self.logger.error(f"Error getting ANTHROPIC_API_KEY: {str(e)}")
                self.logger.exception("Exception details:")
                return
                
            # Prepare headers
            headers = {
                "anthropic-version": "2023-06-01",
                "x-api-key": api_key
            }
            
            # Log headers (excluding API key)
            log_headers = headers.copy()
            log_headers["x-api-key"] = "********"  # Mask the API key in logs
            self.logger.debug(f"Polling headers: {json.dumps(log_headers, indent=2)}")
            
            # Poll until batch is complete or max retries reached
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Get batch status
                    poll_url = f"https://api.anthropic.com/v1/messages/batches/{batch_id}"
                    self.logger.debug(f"Polling batch status from: {poll_url}")
                    
                    # Increase timeout for polling to handle large batches
                    response = requests.get(
                        poll_url,
                        headers=headers,
                        timeout=60  # 1-minute timeout for status check
                    )
                    
                    # Log response status
                    self.logger.debug(f"Batch {batch_id} poll response status: {response.status_code}")
                    
                    # Check for errors
                    response.raise_for_status()
                    result = response.json()
                    
                    # Log batch status for debugging
                    self.logger.info(f"Batch {batch_id} status: {result['processing_status']}")
                    self.logger.info(f"Batch {batch_id} request counts: Processing={result['request_counts']['processing']}, "
                                   f"Succeeded={result['request_counts']['succeeded']}, "
                                   f"Errored={result['request_counts']['errored']}")
                    
                    # Log full response at debug level
                    self.logger.debug(f"Batch {batch_id} full response: {json.dumps(result, indent=2)}")
                    
                    # Update progress tracker
                    self.progress_tracker.update_batch_status(
                        batch_id,
                        result["processing_status"],
                        result["request_counts"]["processing"],
                        result["request_counts"]["succeeded"],
                        result["request_counts"]["errored"]
                    )
                    
                    # Check if batch is complete
                    if result["processing_status"] == "ended":
                        self.logger.info(f"Batch {batch_id} processing ended. Processing results...")
                        
                        # Check if there are any errors
                        if result["request_counts"]["errored"] > 0:
                            self.logger.warning(f"Batch {batch_id} has {result['request_counts']['errored']} errored requests")
                        
                        # Get results
                        if "results_url" in result:
                            self.logger.info(f"Batch {batch_id} has results URL: {result['results_url']}")
                            self._process_batch_results(batch_id, result["results_url"])
                        else:
                            self.logger.error(f"Batch {batch_id} is marked as ended but has no results_url")
                            # Handle as error
                            batch = self.active_batches.get(batch_id)
                            if batch:
                                for request in batch["requests"]:
                                    request["future"].set_exception(
                                        Exception(f"Batch {batch_id} ended without results_url")
                                    )
                        break
                    
                    # Wait before polling again
                    self.logger.debug(f"Waiting {self.polling_interval} seconds before polling batch {batch_id} again (retry {retry_count}/{max_retries})")
                    time.sleep(self.polling_interval)
                    retry_count += 1
                    
                except requests.exceptions.RequestException as e:
                    # Log detailed error information
                    error_detail = ""
                    is_rate_limit_error = False
                    
                    if hasattr(e, 'response') and e.response:
                        try:
                            error_detail = e.response.json()
                            self.logger.error(f"Batch {batch_id} polling error details: {json.dumps(error_detail, indent=2)}")
                            
                            # Check if this is a rate limit error
                            if e.response.status_code == 429:
                                is_rate_limit_error = True
                        except:
                            error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
                            self.logger.error(f"Batch {batch_id} polling error: {error_detail}")
                            
                            # Check if this is a rate limit error
                            if hasattr(e, 'response') and e.response.status_code == 429:
                                is_rate_limit_error = True
                    else:
                        self.logger.error(f"Batch {batch_id} polling error: {str(e)}")
                    
                    # Implement exponential backoff for rate limit errors
                    if is_rate_limit_error:
                        # Calculate backoff time: min(polling_interval * 2^retry_count, 60 seconds)
                        backoff_time = min(self.polling_interval * (2 ** retry_count), 60)
                        self.logger.warning(f"Rate limit exceeded. Backing off for {backoff_time} seconds before retry {retry_count+1}/{max_retries}")
                        time.sleep(backoff_time)
                    else:
                        # For other errors, use the normal polling interval
                        time.sleep(self.polling_interval)
                    
                    retry_count += 1
                except Exception as e:
                    self.logger.error(f"Unexpected error polling batch {batch_id}: {str(e)}")
                    self.logger.exception("Exception details:")
                    time.sleep(self.polling_interval)  # Wait before retrying
                    retry_count += 1
            
            # If we've reached max retries, handle as error
            if retry_count >= max_retries:
                self.logger.error(f"Max polling retries reached for batch {batch_id} after {retry_count * self.polling_interval} seconds ({retry_count} retries)")
                
                # Get the batch
                batch = self.active_batches.get(batch_id)
                if batch:
                    # Handle all requests as failed
                    for request in batch["requests"]:
                        future = request["future"]
                        future_loop = future._loop
                        current_loop = asyncio.get_event_loop()
                        
                        error = Exception(f"Batch polling timed out after {max_retries} retries")
                        
                        if future_loop == current_loop:
                            # Same loop - direct set_exception is safe
                            future.set_exception(error)
                        else:
                            # Different loop - use call_soon_threadsafe
                            self.logger.info(f"Setting exception on future from different loop: future_loop={id(future_loop)}, current_loop={id(current_loop)}")
                            def set_exception_callback():
                                if not future.done():
                                    future.set_exception(error)
                            future_loop.call_soon_threadsafe(set_exception_callback)
                
        except Exception as e:
            logger.error(f"Uncaught exception in poll_for_results thread {thread_id} for batch {batch_id}: {str(e)}")
            logger.exception("Exception details:")
            # Attempt to set up error handling for the batch
            try:
                batch = self.active_batches.get(batch_id)
                if batch:
                    for request in batch["requests"]:
                        try:
                            error = Exception(f"Error in poll_for_results thread: {str(e)}")
                            request["future"].set_exception(error)
                        except Exception as ex:
                            logger.error(f"Failed to set exception on future: {str(ex)}")
            except Exception as ex:
                logger.error(f"Failed to handle error in poll_for_results: {str(ex)}")
    
    def _process_batch_results(self, batch_id: str, results_url: str):
        """
        Process batch results.
        
        Args:
            batch_id: ID of the batch
            results_url: URL to download results from
        """
        self.logger.info(f"Processing results for batch {batch_id} from URL: {results_url}")
        
        # Get API key
        try:
            # Use a different name for os to avoid scope issues
            import os as process_os
            api_key = process_os.getenv("ANTHROPIC_API_KEY")
            self.logger.info(f"In _process_batch_results: ANTHROPIC_API_KEY exists: {api_key is not None}")
            if not api_key:
                self.logger.error("ANTHROPIC_API_KEY environment variable not set")
                return
        except Exception as e:
            self.logger.error(f"Error getting ANTHROPIC_API_KEY: {str(e)}")
            self.logger.exception("Exception details:")
            return
        
        # Prepare headers
        headers = {
            "anthropic-version": "2023-06-01",
            "x-api-key": api_key
        }
        
        # Log headers (excluding API key)
        log_headers = headers.copy()
        log_headers["x-api-key"] = "********"  # Mask the API key in logs
        self.logger.debug(f"Results download headers: {json.dumps(log_headers, indent=2)}")
        
        try:
            # Get results
            self.logger.debug(f"Downloading batch {batch_id} results from URL: {results_url}")
            self.logger.info(f"Using 180-second timeout for downloading results for batch {batch_id}")
            # Increase timeout for results download to handle large batches
            response = requests.get(
                results_url,
                headers=headers,
                timeout=180  # 3-minute timeout for results download
            )
            
            # Log response status
            self.logger.debug(f"Batch {batch_id} results download response status: {response.status_code}")
            
            # Check for errors
            response.raise_for_status()
            
            # Log response content length
            self.logger.debug(f"Batch {batch_id} results content length: {len(response.text)} bytes")
            
            # Save the batch results to a file for inspection
            try:
                import os
                import datetime
                
                # Create logs directory if it doesn't exist
                log_dir = "C:/Users/User/Desktop/ShowupSquaredV4/logs"
                os.makedirs(log_dir, exist_ok=True)
                
                # Generate timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Create file path
                batch_results_file = os.path.join(log_dir, f"batch_results_{batch_id}_{timestamp}.txt")
                
                # Save batch results to file
                with open(batch_results_file, 'w', encoding='utf-8') as f:
                    # Save the raw response
                    f.write(response.text)
                    
                    # Add a more readable version of each result
                    f.write("\n\n=== INDIVIDUAL RESULTS ===\n\n")
                    
                    # Parse each line as JSON
                    for line_num, line in enumerate(response.text.strip().split("\n")):
                        try:
                            result = json.loads(line)
                            f.write(f"\n--- RESULT {line_num+1} (ID: {result.get('custom_id', 'unknown')}) ---\n\n")
                            
                            # Check if the result was successful
                            result_type = result.get("result", {}).get("type", "unknown")
                            f.write(f"Result Type: {result_type}\n")
                            
                            if result_type == "succeeded":
                                # Extract content
                                message = result.get("result", {}).get("message", {})
                                content_array = message.get("content", [])
                                
                                if content_array and isinstance(content_array[0], dict) and "text" in content_array[0]:
                                    content = content_array[0]["text"]
                                    f.write(f"\nCONTENT:\n{content}\n")
                                else:
                                    f.write("\nNo content found in result\n")
                            else:
                                # Extract error information
                                error_info = result.get("result", {}).get("error", {})
                                error_type = error_info.get("type", "unknown")
                                error_message = error_info.get("message", "No error message provided")
                                f.write(f"\nERROR: {error_type}\nMESSAGE: {error_message}\n")
                        except json.JSONDecodeError:
                            f.write(f"\n--- LINE {line_num+1} (Could not parse as JSON) ---\n\n")
                            f.write(line)
                
                self.logger.info(f"Saved batch results to: {batch_results_file}")
                print(f"BATCH RESULTS SAVED: {batch_results_file}")
            except Exception as e:
                self.logger.error(f"Error saving batch results to file: {str(e)}")
            
            # Parse results (JSONL format)
            results = {}
            line_count = 0
            
            # Check if response is empty
            if not response.text.strip():
                self.logger.error(f"Batch {batch_id} results response is empty")
                raise ValueError(f"Empty response from results URL: {results_url}")
            
            # Parse each line as JSON
            for line in response.text.strip().split("\n"):
                line_count += 1
                try:
                    result = json.loads(line)
                    if "custom_id" in result:
                        results[result["custom_id"]] = result
                    else:
                        self.logger.warning(f"Batch {batch_id} result missing custom_id: {line}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON on line {line_count}: {str(e)}")
                    self.logger.error(f"Problematic line content: {line[:100]}...")
            
            self.logger.info(f"Parsed {line_count} result lines for batch {batch_id}, found {len(results)} results with custom_id")
            
            # Process each result
            batch = self.active_batches.get(batch_id)
            if not batch:
                self.logger.error(f"Batch {batch_id} not found in active batches")
                return
            
            # Log batch details
            self.logger.debug(f"Batch {batch_id} has {len(batch['requests'])} requests to process")
                
            successful_requests = []
            failed_requests = []
            
            for request in batch["requests"]:
                custom_id = request["custom_id"]
                self.logger.debug(f"Processing result for request {custom_id}")
                
                if custom_id in results:
                    result = results[custom_id]
                    
                    # Log the result type
                    result_type = result.get("result", {}).get("type", "unknown")
                    self.logger.debug(f"Request {custom_id} result type: {result_type}")
                    
                    if result_type == "succeeded":
                        try:
                            # Extract content
                            message = result.get("result", {}).get("message", {})
                            content_array = message.get("content", [])
                            
                            if not content_array:
                                self.logger.error(f"Request {custom_id} has empty content array")
                                raise ValueError(f"Empty content array in result for request {custom_id}")
                            
                            # Check if the content has the expected structure
                            if not isinstance(content_array[0], dict) or "text" not in content_array[0]:
                                self.logger.error(f"Request {custom_id} has unexpected content structure: {content_array}")
                                raise ValueError(f"Unexpected content structure in result for request {custom_id}")
                            
                            # Extract content safely across threads
                            content = self._extract_content(result, custom_id)
                            
                            # Log content length
                            self.logger.debug(f"Request {custom_id} content length: {len(content)} characters")
                            
                            # Use the safe future resolution method
                            try:
                                # Add diagnostic logging
                                if not asyncio.isfuture(request["future"]):
                                    self.logger.error(f"Request {custom_id} future is not a valid future object: {type(request['future'])}")
                                elif request["future"].done():
                                    self.logger.error(f"Request {custom_id} future is already done. Result: {request['future'].result() if not request['future'].exception() else 'has exception'}")
                                else:
                                    self.logger.info(f"Request {custom_id} future is valid and not done, setting result")
                                
                                # Use the safe method to set the future result
                                self.safely_resolve_future_in_thread(request["future"], task_type="batch_result", request_id=custom_id, content=content)
                                self.logger.info(f"Successfully processed result for request {custom_id}")
                                
                                successful_requests.append(request)
                            except asyncio.InvalidStateError as e:
                                self.logger.error(f"Invalid state error for request {custom_id}: {str(e)}")
                                self.logger.error(f"Future state: done={request['future'].done()}, cancelled={request['future'].cancelled()}")
                                
                                # Cache the result for later recovery
                                cache_batch_results(batch_id, custom_id, content)
                                
                                # Still consider this a successful request
                                successful_requests.append(request)
                                self.logger.info(f"Cached result for request {custom_id} due to invalid state error")
                        except Exception as e:
                            self.logger.error(f"Error extracting content for request {custom_id}: {str(e)}")
                            self.logger.error(f"Result structure: {json.dumps(result, indent=2)}")
                            
                            # Add to failed requests
                            failed_requests.append(request)
                            
                            # Try to set the future exception, but handle invalid state errors
                            try:
                                # Set the future exception
                                request["future"].set_exception(Exception(f"Error extracting content: {str(e)}"))
                            except asyncio.InvalidStateError as ex:
                                self.logger.error(f"Invalid state error setting exception for request {custom_id}: {str(ex)}")
                                self.logger.error(f"Future state: done={request['future'].done()}, cancelled={request['future'].cancelled()}")
                                
                                # Log the original error
                                self.logger.error(f"Original error for request {custom_id}: {str(e)}")
                    else:
                        # Add to failed requests
                        failed_requests.append(request)
                        
                        # Set the future exception with detailed error information
                        error_msg = f"Batch request failed: {result_type}"
                        if "error" in result.get("result", {}):
                            error_info = result["result"]["error"]
                            error_type = error_info.get("type", "unknown")
                            error_message = error_info.get("message", "No error message provided")
                            error_msg += f" - {error_type}: {error_message}"
                            
                            # Log detailed error information
                            self.logger.error(f"Request {custom_id} failed with error: {error_type}")
                            self.logger.error(f"Error message: {error_message}")
                        
                        try:
                            request["future"].set_exception(Exception(error_msg))
                        except asyncio.InvalidStateError as ex:
                            self.logger.error(f"Invalid state error setting exception for request {custom_id}: {str(ex)}")
                            self.logger.error(f"Future state: done={request['future'].done()}, cancelled={request['future'].cancelled()}")
                            self.logger.error(f"Original error message: {error_msg}")
                else:
                    # Add to failed requests
                    failed_requests.append(request)
                    
                    # Set the future exception
                    error_msg = f"No result found for request {custom_id}"
                    self.logger.error(error_msg)
                    try:
                        request["future"].set_exception(Exception(error_msg))
                    except asyncio.InvalidStateError as ex:
                        self.logger.error(f"Invalid state error setting exception for request {custom_id}: {str(ex)}")
                        self.logger.error(f"Future state: done={request['future'].done()}, cancelled={request['future'].cancelled()}")
                        self.logger.error(f"Original error message: {error_msg}")
            
            # Update batch status
            batch["status"] = "completed"
            batch["completed_at"] = datetime.datetime.now()
            batch["successful_requests"] = successful_requests
            batch["failed_requests"] = failed_requests
            
            # Update progress tracker
            self.progress_tracker.update_batch_status(
                batch_id,
                "completed",
                0,
                len(successful_requests),
                len(failed_requests)
            )
            
            # Log completion
            self.logger.info(f"Batch {batch_id} completed: {len(successful_requests)} succeeded, {len(failed_requests)} failed")
            
            # Handle failed requests
            if failed_requests:
                self.logger.info(f"Handling {len(failed_requests)} failed requests for batch {batch_id}")
                self._handle_failed_requests(failed_requests, batch["task_type"])
                
        except requests.exceptions.RequestException as e:
            # Log detailed error information
            error_detail = ""
            is_rate_limit_error = False
            
            if hasattr(e, 'response') and e.response:
                try:
                    error_detail = e.response.json()
                    self.logger.error(f"Batch {batch_id} results download error details: {json.dumps(error_detail, indent=2)}")
                    
                    # Check if this is a rate limit error
                    if e.response.status_code == 429:
                        is_rate_limit_error = True
                except:
                    error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
                    self.logger.error(f"Batch {batch_id} results download error: {error_detail}")
                    
                    # Check if this is a rate limit error
                    if hasattr(e, 'response') and e.response.status_code == 429:
                        is_rate_limit_error = True
            else:
                self.logger.error(f"Batch {batch_id} results download error: {str(e)}")
            
            # For rate limit errors, retry after a delay
            if is_rate_limit_error:
                # Wait for 30 seconds before retrying
                self.logger.warning("Rate limit exceeded when downloading results. Waiting 30 seconds before retrying...")
                time.sleep(30)
                
                # Try again
                try:
                    self.logger.info(f"Retrying download of batch {batch_id} results after rate limit backoff")
                    self._process_batch_results(batch_id, results_url)
                    return  # If successful, return from the method
                except Exception as retry_e:
                    self.logger.error(f"Error retrying batch {batch_id} results download after rate limit: {str(retry_e)}")
            
            # If we get here, either it wasn't a rate limit error or the retry failed
            # Get the batch
            batch = self.active_batches.get(batch_id)
            if batch:
                # Handle all requests as failed
                for request in batch["requests"]:
                    try:
                        request["future"].set_exception(Exception(f"Error downloading batch results: {str(e)}"))
                    except asyncio.InvalidStateError as ex:
                        custom_id = request.get("custom_id", "unknown")
                        self.logger.error(f"Invalid state error setting exception for request {custom_id}: {str(ex)}")
                        self.logger.error(f"Future state: done={request['future'].done()}, cancelled={request['future'].cancelled()}")
                        self.logger.error(f"Original error message: Error downloading batch results: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error processing batch results for {batch_id}: {str(e)}")
            self.logger.exception("Exception details:")
            
            # Get the batch
            batch = self.active_batches.get(batch_id)
            if batch:
                # Handle all requests as failed
                for request in batch["requests"]:
                    try:
                        request["future"].set_exception(Exception(f"Unexpected error processing batch results: {str(e)}"))
                    except asyncio.InvalidStateError as ex:
                        custom_id = request.get("custom_id", "unknown")
                        self.logger.error(f"Invalid state error setting exception for request {custom_id}: {str(ex)}")
                        self.logger.error(f"Future state: done={request['future'].done()}, cancelled={request['future'].cancelled()}")
                        self.logger.error(f"Original error message: Unexpected error processing batch results: {str(e)}")
    
    def _handle_failed_requests(self, failed_requests: List[Dict[str, Any]], task_type: str):
        """
        Handle failed requests by retrying them individually.
        
        Args:
            failed_requests: List of failed request objects
            task_type: Type of task
        """
        self.logger.info(f"Handling {len(failed_requests)} failed requests for task type: {task_type}")
        
        # Retry each failed request individually
        for i, request in enumerate(failed_requests):
            custom_id = request.get("custom_id", f"unknown-{i}")
            self.logger.info(f"Retrying failed request {i+1}/{len(failed_requests)}: {custom_id}")
            
            # Log request details at debug level
            self.logger.debug(f"Request {custom_id} details:")
            self.logger.debug(f"  Model: {request.get('model', 'unknown')}")
            self.logger.debug(f"  Max tokens: {request.get('max_tokens', 'unknown')}")
            self.logger.debug(f"  Temperature: {request.get('temperature', 'unknown')}")
            self.logger.debug(f"  Prompt length: {len(request.get('prompt', ''))} characters")
            
            try:
                self.error_handler.retry_request(request)
                self.logger.info(f"Successfully retried request {custom_id}")
            except Exception as e:
                self.logger.error(f"Error retrying request {custom_id}: {str(e)}")
                self.logger.exception("Exception details:")


    def safely_resolve_future_in_thread(self, future, task_type, request_id, content=None, error=None):
        """
        Safely resolve a future in any thread.
        
        Args:
            future: The future to resolve
            task_type: Type of task for logging
            request_id: ID of the request for logging
            content: Content to set as the result (if not None)
            error: Exception to set (if not None)
        """
        thread_id = threading.get_ident()
        logger.info(f"Thread {thread_id} resolving future for request {request_id}")
        
        try:
            # Ensure we have an event loop in this thread
            try:
                loop = asyncio.get_event_loop()
                if DEBUG_EVENT_LOOPS:
                    logger.info(f"Event loop info in safely_resolve_future_in_thread - Thread {thread_id}: "
                               f"loop={id(loop)}, running={loop.is_running()}")
            except RuntimeError:
                logger.info(f"Thread {thread_id} has no event loop, creating one")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                if DEBUG_EVENT_LOOPS:
                    logger.info(f"New event loop created in Thread {thread_id}: loop={id(loop)}")
                
            # Get the future's loop
            future_loop = future._loop
                
            if error is not None:
                # Setting an exception
                try:
                    if future_loop == loop:
                        # Same loop - direct set_exception is safe
                        if not future.done():
                            future.set_exception(error)
                    else:
                        # Different loop - use call_soon_threadsafe
                        def set_exception_callback():
                            if not future.done():
                                future.set_exception(error)
                        future_loop.call_soon_threadsafe(set_exception_callback)
                    logger.info(f"Set exception on future for request {request_id}")
                except RuntimeError as e:
                    if "There is no current event loop in thread" in str(e):
                        logger.warning(f"Event loop error when setting exception: {str(e)}")
                        # Create event loop if needed
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            logger.info(f"Created new event loop in exception handler: {id(loop)}")
                        # Try again with event loop set
                        if not future.done():
                            future.set_exception(error)
                    else:
                        # Re-raise other RuntimeErrors
                        raise
            elif content is not None:
                # Setting a result
                # Get result directly if done
                if future.done():
                    logger.warning(f"Future for request {request_id} is already done, cannot set result")
                    return
                
                try:
                    if future_loop == loop:
                        # Same loop - direct set_result is safe
                        future.set_result(content)
                    else:
                        # Different loop - use call_soon_threadsafe
                        logger.info(f"Setting result on future from different loop for request {request_id}: future_loop={id(future_loop)}, current_loop={id(loop)}")
                        def set_result_callback():
                            if not future.done():
                                future.set_result(content)
                        future_loop.call_soon_threadsafe(set_result_callback)
                    logger.info(f"Set result on future for request {request_id}")
                except RuntimeError as e:
                    if "There is no current event loop in thread" in str(e):
                        logger.warning(f"Event loop error when setting result: {str(e)}")
                        # Create event loop if needed
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            logger.info(f"Created new event loop in exception handler for result: {id(loop)}")
                        # Try again with event loop set
                        future.set_result(content)
                    else:
                        # Re-raise other RuntimeErrors
                        raise
        except Exception as e:
            logger.error(f"Error resolving future in thread {thread_id}: {str(e)}")
            logger.exception("Exception details:")
            raise
            
    def _extract_content(self, result_data, request_id):
        """
        Extract content from API response safely across threads.
        """
        # Ensure this thread has an event loop
        try:
            loop = asyncio.get_event_loop()
            if DEBUG_EVENT_LOOPS:
                self.logger.info(f"Event loop info in _extract_content - Thread {threading.get_ident()}: "
                                f"loop={id(loop)}, running={loop.is_running()}")
        except RuntimeError:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.logger.info(f"Created new event loop for thread {threading.get_ident()} in _extract_content")
            if DEBUG_EVENT_LOOPS:
                self.logger.info(f"New event loop info - Thread {threading.get_ident()}: "
                                f"loop={id(loop)}, running={loop.is_running()}")
        
        try:
            # Extract content from the result data
            message = result_data.get("result", {}).get("message", {})
            content_array = message.get("content", [])
            
            if not content_array:
                raise ValueError(f"Empty content array in result for request {request_id}")
            
            # Check if the content has the expected structure
            if not isinstance(content_array[0], dict) or "text" not in content_array[0]:
                raise ValueError(f"Unexpected content structure in result for request {request_id}")
            
            content = content_array[0]["text"]
            return content
        except Exception as e:
            self.logger.error(f"Error extracting content for request {request_id}: {str(e)}")
            raise
            
class BatchProcessor:
    """
    Intercepts API calls and manages batching process.
    
    This class is the main entry point for batch processing, intercepting
    API calls and managing the batching process.
    """
    
    def __init__(self, max_batch_size: int = 100, polling_interval: int = 10,
                enabled: bool = True, flush_interval: int = 60):
        """
        Initialize the batch processor.
        
        Args:
            max_batch_size: Maximum number of items in a batch
            polling_interval: Seconds between polling for batch results
            enabled: Whether batch processing is enabled
            flush_interval: Seconds between automatic queue flushes
        """
        self.max_batch_size = max_batch_size
        self.polling_interval = polling_interval
        self.enabled = enabled
        self.flush_interval = flush_interval
        self.request_queues = {}  # Keyed by workflow step
        self.batch_manager = BatchManager(max_batch_size, polling_interval)
        self.progress_tracker = self.batch_manager.progress_tracker
        self.error_handler = self.batch_manager.error_handler
        self.logger = logging.getLogger("batch_processor")
        
        # Initialize task-specific event loops
        self.event_loop = get_or_create_event_loop("default")
        self.logger.debug(f"Using default event loop: {id(self.event_loop)}")
        
        # Add event loop registry
        self._loop_registry = {}  # Map request IDs to their creating event loops
        self.logger.debug("Initialized event loop registry")
        
        # Start the queue flusher thread
        self._start_queue_flusher()
        # Clean up old state and result files
        try:
            clean_up_old_state_files()
            clean_up_old_result_files()
        except Exception as e:
            self.logger.error(f"Error cleaning up old state and result files: {str(e)}")
        
        self.logger.info(f"BatchProcessor initialized (enabled={enabled}, max_batch_size={max_batch_size})")
        
        
    def _start_queue_flusher(self):
        """Start a background thread to periodically flush queues."""
        if self.flush_interval <= 0:
            return
            
        def flush_queues():
            while True:
                time.sleep(self.flush_interval)
                self.flush_all_queues()
                
        flusher_thread = threading.Thread(
            target=flush_queues,
            daemon=True  # Make thread a daemon so it doesn't block program exit
        )
        flusher_thread.start()
        
    def get_request_for_future(self, future: asyncio.Future) -> Optional[Dict[str, Any]]:
        """
        Get the request object for a given future.
        
        Args:
            future: The future object to find the request for
            
        Returns:
            The request object if found, None otherwise
        """
        # Search for the future in all request queues
        for task_type, requests in self.request_queues.items():
            for request in requests:
                if request.get("future") == future:
                    return request
        
        # Search for the future in active batches
        for batch_id, batch in self.batch_manager.active_batches.items():
            for request in batch.get("requests", []):
                if request.get("future") == future:
                    return request
        
        return None
    
    def intercept_api_call(self, prompt: str, system_prompt: str, model: str,
                          max_tokens: int, temperature: float, task_type: str) -> asyncio.Future:
        """
        Intercept an API call and add it to the appropriate queue.
        
        Args:
            prompt: The prompt to send to Claude
            system_prompt: Optional system prompt
            model: Claude model to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature setting
            task_type: Type of task (e.g., "content_generation", "content_review")
            
        Returns:
            A future object that will eventually contain the response
        """
        # If batch processing is disabled, raise an exception
        if not self.enabled:
            raise ValueError("Batch processing is disabled")
            
        # Get the task-specific event loop
        loop = get_or_create_event_loop(task_type)
        self.logger.debug(f"Using task-specific event loop {id(loop)} for task type {task_type}")
        
        # Generate a unique ID for this request
        request_id = f"{task_type}_{str(uuid.uuid4())}"
        
        # Create a request object
        request = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "task_type": task_type,
            "custom_id": request_id,
            "created_at": datetime.datetime.now()
        }
        
        # Add to the appropriate queue
        if task_type not in self.request_queues:
            self.request_queues[task_type] = []
        
        # Create a future for this request
        future = loop.create_future()
        
        # Store the loop in the request dictionary
        request["loop"] = loop
        request["future"] = future
        
        # Register the loop for this request
        self._loop_registry[request_id] = loop
        
        # Add to queue
        self.request_queues[task_type].append(request)
        
        self.logger.info(f"Added request to {task_type} queue (queue size: {len(self.request_queues[task_type])})")
        
        # Check if we have enough requests to form a batch
        if len(self.request_queues[task_type]) >= self.max_batch_size:
            self.logger.info(f"Queue for {task_type} reached max batch size ({self.max_batch_size}), processing queue")
            self._process_queue(task_type)
        
        return future
    
    def _process_queue(self, task_type: str):
        """
        Process a queue of requests by creating and submitting a batch.
        
        Args:
            task_type: Type of task to process
        """
        # Get the requests for this task type
        requests = self.request_queues[task_type]
        if not requests:
            self.logger.debug(f"No requests in queue for {task_type}, nothing to process")
            return
            
        self.logger.info(f"Processing queue for {task_type} with {len(requests)} requests")
        
        # Clear the queue
        self.request_queues[task_type] = []
        self.logger.debug(f"Cleared queue for {task_type}, queue is now empty")
        
        # Submit the batch
        self.logger.info(f"Submitting batch of {len(requests)} requests for {task_type}")
        self.batch_manager.submit_batch(requests, task_type)
        self.logger.debug(f"Batch submitted for {task_type}, queue size is now {len(self.request_queues[task_type])}")
    
    def flush_queue(self, task_type: str):
        """
        Flush a queue by processing all requests in it.
        
        Args:
            task_type: Type of task to flush
        """
        if task_type in self.request_queues and self.request_queues[task_type]:
            self.logger.info(f"Flushing queue for {task_type} with {len(self.request_queues[task_type])} requests")
            self._process_queue(task_type)
    
    def flush_all_queues(self):
        """Flush all queues by processing all requests in them."""
        self.logger.info(f"Flushing all queues: {self.get_queue_sizes()}")
        for task_type in list(self.request_queues.keys()):
            self.flush_queue(task_type)
    
    def clear_all_queues(self):
        """Clear all queues without processing the requests."""
        self.logger.info(f"Clearing all queues: {self.get_queue_sizes()}")
        for task_type in list(self.request_queues.keys()):
            if task_type in self.request_queues:
                # Get the requests for this task type
                requests = self.request_queues[task_type]
                if requests:
                    self.logger.info(f"Clearing {len(requests)} requests from {task_type} queue without processing")
                    
                    # Set all futures to cancelled state
                    try:
                        for request in requests:
                            if "future" in request and request["future"] is not None:
                                if not request["future"].done():
                                    request["future"].cancel()
                                    self.logger.debug(f"Cancelled future for request {request.get('custom_id', 'unknown')}")
                    except Exception as e:
                        self.logger.error(f"Error cancelling futures for {task_type} queue: {str(e)}")
                
                # Clear the queue
                self.request_queues[task_type] = []
                self.logger.debug(f"Cleared queue for {task_type}, queue is now empty")
    
    def _validate_event_loop(self, request_id, loop=None):
        """
        Validate that the current event loop matches the one stored for this request.
        
        Args:
            request_id: The ID of the request
            loop: The loop to validate against (optional)
            
        Returns:
            bool: True if the loops match, False otherwise
        """
        if loop is None:
            loop = asyncio.get_event_loop()
        
        if request_id not in self._loop_registry:
            self.logger.warning(f"No event loop registered for request {request_id}")
            return False
        
        registered_loop = self._loop_registry[request_id]
        if registered_loop != loop:
            self.logger.warning(f"Event loop mismatch for request {request_id}. Registered: {id(registered_loop)}, Current: {id(loop)}")
            return False
        
        self.logger.debug(f"Event loop validated for request {request_id}: {id(loop)}")
        return True
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """
        Get the sizes of all queues.
        
        Returns:
            Dictionary mapping task types to queue sizes
        """
        return {task_type: len(queue) for task_type, queue in self.request_queues.items()}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the batch processor.
        
        Returns:
            Status dictionary
        """
        queue_sizes = self.get_queue_sizes()
        batch_summary = self.progress_tracker.get_summary()
        
        return {
            "enabled": self.enabled,
            "max_batch_size": self.max_batch_size,
            "queue_sizes": queue_sizes,
            "total_queued": sum(queue_sizes.values()),
            "active_batches": batch_summary["active_batches"],
            "completed_batches": batch_summary["completed_batches"],
            "total_requests_processed": batch_summary["succeeded_requests"] + batch_summary["errored_requests"],
            "succeeded_requests": batch_summary["succeeded_requests"],
            "errored_requests": batch_summary["errored_requests"],
            "processing_requests": batch_summary["processing_requests"],
            "registered_loops": len(self._loop_registry)
        }


# Dictionary of batch processor instances, keyed by instance_id
_batch_processors = {}

def get_batch_processor(instance_id: str = "default", max_batch_size: int = 100,
                       polling_interval: int = 10, enabled: bool = True,
                       flush_interval: int = 60) -> BatchProcessor:
    """
    Get a batch processor instance for a specific application instance.
    
    Args:
        instance_id: The ID of the application instance
        max_batch_size: Maximum number of items in a batch
        polling_interval: Seconds between polling for batch results
        enabled: Whether batch processing is enabled
        flush_interval: Seconds between automatic queue flushes
        
    Returns:
        BatchProcessor instance
    """
    global _batch_processors
    
    # Create a new batch processor for this instance if it doesn't exist
    if instance_id not in _batch_processors:
        logger.info(f"Creating new batch processor for instance {instance_id}")
        _batch_processors[instance_id] = BatchProcessor(
            max_batch_size=max_batch_size,
            polling_interval=polling_interval,
            enabled=enabled,
            flush_interval=flush_interval
        )
    
    return _batch_processors[instance_id]