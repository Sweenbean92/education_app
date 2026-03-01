import json
import os
from pathlib import Path

def _get_project_root():
    """Get the project root directory by looking for common project markers"""
    current = Path(__file__).resolve()
    
    # Look for project root markers (like .git, requirements.txt, etc.)
    for parent in [current] + list(current.parents):
        if (parent / 'rag_chain.py').exists() or (parent / 'app.py').exists():
            return parent
    
    # Fallback: use the directory containing model_logger.py
    return current.parent

class ModelLogger:
    """Logs model interactions including queries, responses, and metadata"""
    
    def __init__(self, log_dir=None):
        if log_dir is None:
            # Use project root / logs
            project_root = _get_project_root()
            self.log_dir = project_root / "logs"
        else:
            self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        # Separate log files for different types
        self.log_file = self.log_dir / "model_responses.jsonl"  # General/chat logs
        self.questions_file = self.log_dir / "questions.jsonl"  # Question generation
        self.feedback_file = self.log_dir / "feedback.jsonl"  # Answer evaluations
        self.teaching_material_file = self.log_dir / "teaching_material.jsonl"  # Teaching material
        self.error_focused_learning_file = self.log_dir / "error_focused_learning.jsonl"  # Error-focused learning
    
    def _write_log(self, log_entry, log_file=None):
        """Write a log entry to the specified JSONL file"""
        if log_file is None:
            log_file = self.log_file
        try:
            # Ensure the directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            # Write the log entry
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                f.flush()  # Ensure data is written immediately
        except Exception as e:
            print(f"Error writing log to {log_file}: {e}")
            import traceback
            traceback.print_exc()
    
    def log_chat_response(self, query, response, model, context=None, execution_time=None):
        """Log a chat response"""
        log_entry = {
            "type": "chat",
            "model": model,
            "query": query,
            "response": response,
            "response_length": len(response) if response else 0,
            "context_used": context is not None
        }
        if execution_time is not None:
            log_entry["execution_time"] = execution_time
        if context:
            log_entry["context_preview"] = context[:200] + "..." if len(context) > 200 else context
        self._write_log(log_entry)
    
    def log_teaching_material(self, topic, material, model, context=None, performance_level=None, execution_time=None):
        """
        Log generated teaching material.
        
        Args:
            execution_time: Execution time in seconds (float)
        """
        log_entry = {
            "type": "teaching_material",
            "model": model,
            "topic": topic or "general",
            "material": material,
            "material_length": len(material) if material else 0,
            "context_used": context is not None
        }
        if execution_time is not None:
            log_entry["execution_time"] = execution_time
        if performance_level:
            log_entry["performance_level"] = performance_level
        if context:
            log_entry["context_preview"] = context[:200] + "..." if len(context) > 200 else context
        self._write_log(log_entry, self.teaching_material_file)
        return log_entry
    
    def log_question_generation(self, topic, question, model, context=None, performance_level=None, execution_time=None):
        """
        Log a generated quiz question.
        
        Args:
            execution_time: Execution time in seconds (float)
        """
        log_entry = {
            "type": "question_generation",
            "model": model,
            "topic": topic or "general",
            "question": question,
            "question_length": len(question) if question else 0,
            "context_used": context is not None
        }
        if execution_time is not None:
            log_entry["execution_time"] = execution_time
        if performance_level:
            log_entry["performance_level"] = performance_level
        if context:
            log_entry["context_preview"] = context[:200] + "..." if len(context) > 200 else context
        self._write_log(log_entry, self.questions_file)
        return log_entry  # Return for potential linking
    
    def log_answer_evaluation(self, question, student_answer, explanation, model, context=None, performance_level=None, execution_time=None, feedback_type=None):
        """Log an answer evaluation - includes the full question and evaluation
        
        Args:
            execution_time: Execution time in seconds (float)
            feedback_type: Type of feedback being evaluated (e.g., "correct", "incorrect", "partially_correct", "incomplete")
        """
        log_entry = {
            "type": "answer_evaluation",
            "model": model,
            "question": question,  # Full question text
            "question_length": len(question) if question else 0,
            "student_answer": student_answer,
            "student_answer_length": len(student_answer) if student_answer else 0,
            "explanation": explanation,  # Full evaluation/explanation
            "explanation_length": len(explanation) if explanation else 0,
            "context_used": context is not None
        }
        if execution_time is not None:
            log_entry["execution_time"] = execution_time
        if performance_level:
            log_entry["performance_level"] = performance_level
        if feedback_type:
            log_entry["feedback_type"] = feedback_type
        if context:
            log_entry["context_preview"] = context[:200] + "..." if len(context) > 200 else context
        self._write_log(log_entry, self.feedback_file)
        return log_entry
    
    def log_error_focused_learning(self, test_case_id=None, topic=None, question=None, student_solution=None, 
                                   error_type=None, root_cause=None, learning_response=None, response_length=None,
                                   execution_time=None, performance_level=None, model=None, max_tokens=None, 
                                   num_ctx=None, context_preview=None, template_echo_detected=None,
                                   expected_components=None, components_covered=None, coverage_rate=None,
                                   components_missed=None, error_identified=None, root_cause_explained=None,
                                   learning_materials_suggested=None, indicator_score=None, error_focused_score=None):
        """
        Log error-focused learning response with all fields matching the test output format.
        
        This method accepts all fields that are produced by the error-focused learning test
        to ensure identical JSON output format.
        """
        log_entry = {
            "type": "error_focused_learning",
            "model": model,
            "topic": topic,
            "question": question,
            "student_solution": student_solution,
            "error_type": error_type,
            "root_cause": root_cause,
            "learning_response": learning_response,
            "response_length": response_length if response_length is not None else (len(learning_response) if learning_response else 0),
            "context_used": context_preview is not None
        }
        
        # Add optional fields if provided
        if execution_time is not None:
            log_entry["execution_time"] = execution_time
        if performance_level:
            log_entry["performance_level"] = performance_level
        if max_tokens is not None:
            log_entry["max_tokens"] = max_tokens
        if num_ctx is not None:
            log_entry["num_ctx"] = num_ctx
        if context_preview:
            log_entry["context_preview"] = context_preview
        if template_echo_detected is not None:
            log_entry["template_echo_detected"] = template_echo_detected
        if expected_components is not None:
            log_entry["expected_components"] = expected_components
        if components_covered is not None:
            log_entry["components_covered"] = components_covered
        if coverage_rate is not None:
            log_entry["coverage_rate"] = coverage_rate
        if components_missed is not None:
            log_entry["components_missed"] = components_missed
        if error_identified is not None:
            log_entry["error_identified"] = error_identified
        if root_cause_explained is not None:
            log_entry["root_cause_explained"] = root_cause_explained
        if learning_materials_suggested is not None:
            log_entry["learning_materials_suggested"] = learning_materials_suggested
        if indicator_score is not None:
            log_entry["indicator_score"] = indicator_score
        if error_focused_score is not None:
            log_entry["error_focused_score"] = error_focused_score
        if test_case_id is not None:
            log_entry["test_case_id"] = test_case_id
        
        self._write_log(log_entry, self.error_focused_learning_file)
        return log_entry
    
    def get_logs(self, log_type=None, model=None, limit=100):
        """Retrieve logs with optional filtering from appropriate log files"""
        logs = []
        log_files = []
        
        # Determine which log files to read based on log_type
        if log_type == "question_generation":
            log_files = [self.questions_file]
        elif log_type == "answer_evaluation":
            log_files = [self.feedback_file]
        elif log_type == "teaching_material":
            log_files = [self.teaching_material_file]
        elif log_type == "error_focused_learning":
            log_files = [self.error_focused_learning_file]
        elif log_type == "chat":
            log_files = [self.log_file]
        else:
            # If no specific type, read from all files
            log_files = [self.log_file, self.questions_file, self.feedback_file, self.teaching_material_file, self.error_focused_learning_file]
        
        try:
            for log_file in log_files:
                if not log_file.exists():
                    continue
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                log_entry = json.loads(line)
                                # Apply filters
                                if log_type and log_entry.get("type") != log_type:
                                    continue
                                if model and log_entry.get("model") != model:
                                    continue
                                logs.append(log_entry)
                            except json.JSONDecodeError:
                                continue
            
            # Return most recent logs first, limit results
            logs.reverse()
            return logs[:limit]
        except Exception as e:
            print(f"Error reading logs: {e}")
            return logs
    
    def get_statistics(self):
        """Get statistics about logged interactions from all log files"""
        stats = {
            "total_logs": 0,
            "by_type": {},
            "by_model": {},
            "total_responses_length": 0
        }
        
        # Read from all log files
        log_files = [self.log_file, self.questions_file, self.feedback_file, self.teaching_material_file, self.error_focused_learning_file]
        
        try:
            for log_file in log_files:
                if not log_file.exists():
                    continue
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                log_entry = json.loads(line)
                                stats["total_logs"] += 1
                                
                                # Count by type
                                log_type = log_entry.get("type", "unknown")
                                stats["by_type"][log_type] = stats["by_type"].get(log_type, 0) + 1
                                
                                # Count by model
                                model = log_entry.get("model", "unknown")
                                stats["by_model"][model] = stats["by_model"].get(model, 0) + 1
                                
                                # Sum response lengths
                                response_length = log_entry.get("response_length", 0) or \
                                                log_entry.get("question_length", 0) or \
                                                log_entry.get("explanation_length", 0) or \
                                                log_entry.get("material_length", 0) or \
                                                log_entry.get("learning_response", "")
                                if isinstance(response_length, str):
                                    response_length = len(response_length)
                                stats["total_responses_length"] += response_length
                            except json.JSONDecodeError:
                                continue
            
            return stats
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return stats

# Global logger instance
logger = ModelLogger()

