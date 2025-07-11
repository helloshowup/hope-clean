"""Learning Context Manager for Student Simulation

Manages tracking of student knowledge and learning progression across lessons.
"""

import os
import json
import re
import difflib
import logging
from datetime import datetime
logger = logging.getLogger("output_library_editor")

class LearningContextManager:
    """Manages the learning context for simulating student knowledge over time."""
    
    def __init__(self):
        """Initialize the learning context manager."""
        self.context_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "showup-data", "student_learning_context")
        
        # Create the context directory if it doesn't exist
        os.makedirs(self.context_dir, exist_ok=True)
        
        # Default empty context
        self.default_context = {
            "profile_id": "",
            "last_update": "",
            "lessons_completed": [],
            "knowledge_concepts": {},
            "recurring_questions": [],
            "examples_seen": {},  # New field for tracking specific examples
            "emotional_development": {
                "confidence": {"trend": "neutral", "areas_of_concern": []},
                "engagement": {"trend": "neutral", "notes": ""}
            }
        }
        
        # Enable semantic analysis by default
        self.use_semantic_analysis = True
    
    def get_context_file_path(self, profile_name):
        """Get the file path for a specific profile's learning context."""
        # Sanitize profile name for file usage
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', profile_name)
        return os.path.join(self.context_dir, f"{safe_name}_learning_context.json")
    
    def load_learning_context(self, profile_name):
        """Load the learning context for a profile."""
        context_file = self.get_context_file_path(profile_name)
        
        if os.path.exists(context_file):
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    context = json.load(f)
                    logger.info(f"Loaded learning context for profile: {profile_name}")
                    return context
            except Exception as e:
                logger.error(f"Error loading learning context: {str(e)}")
                return self._create_new_context(profile_name)
        else:
            return self._create_new_context(profile_name)
    
    def _create_new_context(self, profile_name):
        """Create a new learning context for a profile."""
        context = self.default_context.copy()
        context["profile_id"] = profile_name
        context["last_update"] = datetime.datetime.now().isoformat()
        return context
    
    def save_learning_context(self, profile_name, context):
        """Save the learning context for a profile."""
        context_file = self.get_context_file_path(profile_name)
        
        try:
            # Update the last update timestamp
            context["last_update"] = datetime.datetime.now().isoformat()
            
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2)
                
            logger.info(f"Saved learning context for profile: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving learning context: {str(e)}")
            return False
    
    def update_from_lesson(self, profile_name, lesson_file, response):
        """Update the learning context based on lesson response."""
        # Load the current context
        context = self.load_learning_context(profile_name)
        
        # Add the lesson to completed lessons if not already there
        lesson_name = os.path.basename(lesson_file)
        if lesson_name not in context["lessons_completed"]:
            context["lessons_completed"].append(lesson_name)
            
        # Check if we should use semantic analysis or regex
        try:
            # Try to use semantic analysis if available
            if hasattr(self, 'use_semantic_analysis') and self.use_semantic_analysis:
                updated_context = self._semantic_context_update(context, response, lesson_name)
                if updated_context:
                    # Merge the updated context with any new lesson information
                    updated_context["lessons_completed"] = context["lessons_completed"]
                    context = updated_context
                else:
                    # Fall back to regex approach if semantic analysis fails
                    logger.warning("Semantic analysis failed, falling back to regex pattern matching")
                    self._update_context_with_regex(context, response, lesson_name)
            else:
                # Use the regex approach as before
                self._update_context_with_regex(context, response, lesson_name)
        except Exception as e:
            logger.error(f"Error in context update: {str(e)}. Falling back to regex.")
            self._update_context_with_regex(context, response, lesson_name)
        
        # Save the updated context
        self.save_learning_context(profile_name, context)
        
        return context
        
    def _update_context_with_regex(self, context, response, lesson_name):
        """Update context using regex pattern matching (legacy approach)."""
        # Extract key concepts from the response using regex
        concepts = self._extract_concepts(response)
        for concept, details in concepts.items():
            if concept in context["knowledge_concepts"]:
                # Update existing concept
                current = context["knowledge_concepts"][concept]
                current["familiarity"] = max(current["familiarity"], details["familiarity"])
                current["notes"] = details["notes"]
            else:
                # Add new concept
                context["knowledge_concepts"][concept] = {
                    "familiarity": details["familiarity"],
                    "first_encountered": lesson_name,
                    "notes": details["notes"]
                }
        
        # Extract questions
        questions = self._extract_questions(response)
        for question in questions:
            # Check if this is a recurring question
            found = False
            for q in context["recurring_questions"]:
                if self._are_questions_similar(q["question"], question):
                    if lesson_name not in q["asked_in"]:
                        q["asked_in"].append(lesson_name)
                    found = True
                    break
            
            if not found:
                context["recurring_questions"].append({
                    "question": question,
                    "asked_in": [lesson_name]
                })
        
        # Update emotional development
        self._update_emotional_development(context, response)
        
        return context
    
    def _extract_concepts(self, response):
        """Extract key concepts and familiarity from the response."""
        concepts = {}
        
        # Simple extraction based on key concepts section
        key_concepts_match = re.search(r'## Key Concepts(.*?)##', response, re.DOTALL)
        if key_concepts_match:
            key_concepts_text = key_concepts_match.group(1)
            concept_items = re.findall(r'-\s*(.*?)(?=\n-|\n\n|$)', key_concepts_text, re.DOTALL)
            
            for item in concept_items:
                # For simplicity, use the first few words as the concept name
                words = item.strip().split()
                if len(words) >= 3:
                    concept_name = '_'.join(words[:3]).lower()
                    concepts[concept_name] = {
                        "familiarity": 3,  # Default medium familiarity
                        "notes": item.strip()
                    }
        
        # Extract understanding level
        understanding_match = re.search(r'## Understanding Level\s*(\d)/5', response)
        if understanding_match:
            familiarity = int(understanding_match.group(1))
            # Apply this familiarity to all concepts extracted
            for concept in concepts:
                concepts[concept]["familiarity"] = familiarity
        
        return concepts
    
    def _extract_questions(self, response):
        """Extract questions from the response."""
        questions = []
        
        questions_match = re.search(r'## Questions(.*?)##', response, re.DOTALL)
        if questions_match:
            questions_text = questions_match.group(1)
            question_items = re.findall(r'-\s*(.*?)(?=\n-|\n\n|$)', questions_text, re.DOTALL)
            
            for item in question_items:
                questions.append(item.strip())
        
        return questions
    
    def _are_questions_similar(self, q1, q2):
        """Determine if two questions are similar.
        
        This is a simple implementation - in practice you would use
        semantic similarity measures.
        """
        # Convert to lowercase and remove punctuation for comparison
        q1 = q1.lower().strip('?!. ')
        q2 = q2.lower().strip('?!. ')
        
        # Use difflib to check similarity
        similarity = difflib.SequenceMatcher(None, q1, q2).ratio()
        return similarity > 0.8
    
    def _semantic_context_update(self, context, response, lesson_name):
        """Update learning context using semantic analysis via API call."""
        try:
            # Import the prompt manager for API access
            from .prompt_manager import AIManager
            ai_manager = AIManager()
            
            # Create a system prompt for the analysis
            system_prompt = """You are an expert educational analyst specializing in tracking learning progression.
            Analyze the student's previous knowledge state and their response to a new lesson.
            Your task is to update the learning context based on what they've learned in this lesson."""
            
            # Create the user prompt with the context and response
            user_prompt = f"""
            PREVIOUS LEARNING CONTEXT:
            {json.dumps(context, indent=2)}
            
            NEW LESSON RESPONSE:
            {response}
            
            TASK:
            1. Identify all concepts the student now understands, including those from previous lessons
            2. Extract specific examples used in the lesson
            3. Determine if examples repeat from previous lessons
            4. Identify recurring questions and knowledge gaps
            5. Assess emotional progression and engagement
            
            Respond with a structured JSON object containing the updated learning context.
            Your response should strictly follow this format:
            {{"knowledge_concepts": {{
                "concept_name": {{
                  "familiarity": 1-5,
                  "first_encountered": "lesson_name",
                  "notes": "description"
                }},
                ...
              }},
              "recurring_questions": [
                {{
                  "question": "text",
                  "asked_in": ["lesson_names"]
                }},
                ...
              ],
              "examples_seen": {{
                "example_id": {{
                  "first_seen_in": "lesson_name",
                  "repetition_count": number,
                  "description": "text"
                }},
                ...
              }},
              "emotional_development": {{
                "confidence": {{"trend": "increasing/decreasing/neutral", "areas_of_concern": []}},
                "engagement": {{"trend": "high/medium/low", "notes": ""}}
              }}
            }}
            """
            
            # Make the API call
            logger.info("Making semantic analysis API call for learning context update")
            result = ai_manager.call_claude_api(system=system_prompt, prompt=user_prompt)
            
            # Parse the JSON response
            # Find JSON content between triple backticks if present
            json_match = re.search(r'```json\s*(.+?)\s*```', result, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # Otherwise try to parse the entire response
                json_content = result
                
            updated_context = json.loads(json_content)
            
            # Ensure the basic structure is maintained
            required_keys = ["knowledge_concepts", "recurring_questions", "emotional_development"]
            for key in required_keys:
                if key not in updated_context:
                    logger.warning(f"Missing required key {key} in semantic analysis result")
                    return None
            
            # Add examples_seen if it wasn't in the original context
            if "examples_seen" in updated_context and "examples_seen" not in context:
                context["examples_seen"] = {}
                
            logger.info("Successfully updated context using semantic analysis")
            return updated_context
            
        except Exception as e:
            logger.error(f"Error in semantic context update: {str(e)}")
            return None
    
    def _update_emotional_development(self, context, response):
        """Update emotional development based on the response."""
        emotional_match = re.search(r'## Emotional Response(.*?)##', response, re.DOTALL)
        if emotional_match:
            emotional_text = emotional_match.group(1).lower()
            
            # Update confidence trend
            confidence_terms = {
                'increasing': ['confident', 'comfortable', 'understand', 'grasp', 'mastery'],
                'decreasing': ['confused', 'lost', 'difficult', 'struggle', 'overwhelming', 'uncertain']
            }
            
            # Simple sentiment analysis
            increasing_matches = sum(1 for term in confidence_terms['increasing'] if term in emotional_text)
            decreasing_matches = sum(1 for term in confidence_terms['decreasing'] if term in emotional_text)
            
            if increasing_matches > decreasing_matches:
                context['emotional_development']['confidence']['trend'] = 'increasing'
            elif decreasing_matches > increasing_matches:
                context['emotional_development']['confidence']['trend'] = 'decreasing'
            else:
                context['emotional_development']['confidence']['trend'] = 'neutral'
            
            # Extract areas of concern
            concern_patterns = ['struggle with', 'unclear about', 'confused by', 'difficulty understanding']
            concerns = []
            
            for pattern in concern_patterns:
                matches = re.findall(f"{pattern}\s+([^,.]+)[,.]?", emotional_text)
                concerns.extend(matches)
            
            if concerns:
                context['emotional_development']['confidence']['areas_of_concern'] = concerns
            
            # Update engagement
            engagement_terms = {
                'high': ['excited', 'interesting', 'engaged', 'curious', 'fascinated', 'eager'],
                'low': ['bored', 'uninterested', 'disengaged', 'tedious', 'repetitive', 'dull']
            }
            
            high_matches = sum(1 for term in engagement_terms['high'] if term in emotional_text)
            low_matches = sum(1 for term in engagement_terms['low'] if term in emotional_text)
            
            if high_matches > low_matches:
                context['emotional_development']['engagement']['trend'] = 'high'
            elif low_matches > high_matches:
                context['emotional_development']['engagement']['trend'] = 'low'
            else:
                context['emotional_development']['engagement']['trend'] = 'neutral'
    
    def format_context_for_prompt(self, context):
        """Format the learning context for inclusion in an AI prompt."""
        # Create a prompt-friendly version of the context
        formatted_context = """Previous Learning Context:

"""
        
        # Add completed lessons
        if context["lessons_completed"]:
            formatted_context += "Previously completed lessons:\n"
            for lesson in context["lessons_completed"]:
                formatted_context += f"- {lesson}\n"
            formatted_context += "\n"
        
        # Add known concepts
        if context["knowledge_concepts"]:
            formatted_context += "Concepts already understood:\n"
            for concept, details in context["knowledge_concepts"].items():
                familiarity_level = "basic" if details["familiarity"] <= 2 else \
                                   "good" if details["familiarity"] == 3 else "strong"
                formatted_context += f"- {concept.replace('_', ' ')} ({familiarity_level} understanding): {details['notes']}\n"
            formatted_context += "\n"
        
        # Add recurring questions
        if context["recurring_questions"]:
            formatted_context += "Questions that remain unanswered across multiple lessons:\n"
            for question in context["recurring_questions"]:
                if len(question["asked_in"]) > 1:  # Only include if asked multiple times
                    formatted_context += f"- {question['question']}\n"
            formatted_context += "\n"
        
        # Add examples seen (from semantic analysis)
        if "examples_seen" in context and context["examples_seen"]:
            formatted_context += "Examples previously encountered:\n"
            for example_id, details in context["examples_seen"].items():
                repetition = "" if details["repetition_count"] <= 1 else f" (seen {details['repetition_count']} times)"
                formatted_context += f"- {details['description']}{repetition}\n"
            formatted_context += "\n"
        
        # Add emotional development
        formatted_context += "Current learning state:\n"
        confidence_trend = context["emotional_development"]["confidence"]["trend"]
        formatted_context += f"- Confidence: {confidence_trend}\n"
        
        if context["emotional_development"]["confidence"]["areas_of_concern"]:
            formatted_context += "- Areas of concern: "
            formatted_context += ", ".join(context["emotional_development"]["confidence"]["areas_of_concern"])
            formatted_context += "\n"
        
        engagement_trend = context["emotional_development"]["engagement"]["trend"]
        formatted_context += f"- Engagement level: {engagement_trend}\n"
        
        if context["emotional_development"]["engagement"]["notes"]:
            formatted_context += f"- Engagement notes: {context['emotional_development']['engagement']['notes']}\n"
        
        return formatted_context
