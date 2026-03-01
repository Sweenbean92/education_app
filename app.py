from flask import Flask, render_template, request, jsonify, Response, redirect
from rag_chain import RAGChain
from model_logger import logger
import json
import random
import os
import time

app = Flask(__name__)

# Initialize RAG chain with SmollM2 model (default: temperature 0.1, max_tokens 2048, num_ctx 4096)
rag_chain = RAGChain(model_name="smollm2:360m", temperature=0.1, max_tokens=2048, num_ctx=4096)

def remove_repetitive_content(text, min_repeat_length=100):
    """
    Remove repetitive content from generated text by detecting repeated sequences.
    
    Args:
        text: The text to clean
        min_repeat_length: Minimum length of sequence to consider as repetition (in characters)
    
    Returns:
        Cleaned text with repetitive sections removed
    """
    if not text or len(text) < min_repeat_length * 2:
        return text
    
    # Split text into sentences/paragraphs for better detection
    # Look for repeated blocks of text
    text_length = len(text)
    
    # Check for repetition by comparing chunks
    chunk_size = min_repeat_length
    max_chunks = text_length // chunk_size
    
    if max_chunks < 2:
        return text
    
    # Find the first occurrence of a repeated chunk
    for i in range(max_chunks - 1):
        chunk1_start = i * chunk_size
        chunk1_end = min((i + 1) * chunk_size, text_length)
        chunk1 = text[chunk1_start:chunk1_end]
        
        # Look for this chunk repeating later
        for j in range(i + 1, max_chunks):
            chunk2_start = j * chunk_size
            chunk2_end = min((j + 1) * chunk_size, text_length)
            chunk2 = text[chunk2_start:chunk2_end]
            
            # If chunks are very similar (80% similarity), consider it repetition
            if chunk1 and chunk2:
                similarity = sum(a == b for a, b in zip(chunk1[:min(len(chunk1), len(chunk2))], chunk2[:min(len(chunk1), len(chunk2))])) / max(len(chunk1), len(chunk2))
                if similarity > 0.8:
                    # Found repetition - truncate at the start of the repeated section
                    return text[:chunk2_start].strip()
    
    # Also check for exact repeated phrases (shorter sequences)
    lines = text.split('\n')
    seen_lines = set()
    cleaned_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        # Skip empty lines and very short lines
        if len(line_stripped) < 20:
            cleaned_lines.append(line)
            continue
        
        # Create a normalized version for comparison (remove extra whitespace)
        normalized = ' '.join(line_stripped.split())
        
        # If we've seen this exact line recently (within last 5 lines), skip it
        if normalized in seen_lines:
            # Check if this is part of a repeating pattern
            if len(cleaned_lines) >= 5:
                recent_lines = [l.strip() for l in cleaned_lines[-5:]]
                if normalized in recent_lines:
                    continue  # Skip this repeated line
        
        seen_lines.add(normalized)
        cleaned_lines.append(line)
        
        # Keep only recent lines in memory to avoid memory issues
        if len(seen_lines) > 50:
            # Remove oldest entries (simple approach: keep last 30)
            seen_lines = set(list(seen_lines)[-30:])
    
    result = '\n'.join(cleaned_lines)
    
    # Final check: if the result is significantly shorter, it likely had repetition
    # But we want to preserve the content, so return what we have
    return result

def get_performance_level(max_tokens, num_ctx):
    """Determine performance level from max_tokens and num_ctx values"""
    performance_configs = {
        'low': {'max_tokens': 512, 'num_ctx': 2048},
        'medium': {'max_tokens': 1024, 'num_ctx': 4096},
        'high': {'max_tokens': 2048, 'num_ctx': 6144},
        'ultra': {'max_tokens': 4096, 'num_ctx': 8192}
    }
    
    # Find matching performance level
    for level, config in performance_configs.items():
        if max_tokens == config['max_tokens'] and num_ctx == config['num_ctx']:
            return level
    
    # If no exact match, return 'unknown' or try to determine closest match
    # For simplicity, we'll use ranges
    if max_tokens <= 512 and num_ctx <= 2048:
        return 'low'
    elif max_tokens <= 1024 and num_ctx <= 4096:
        return 'medium'
    elif max_tokens <= 2048 and num_ctx <= 6144:
        return 'high'
    elif max_tokens <= 4096 and num_ctx <= 8192:
        return 'ultra'
    else:
        return 'custom'

@app.route('/')
def index():
    return redirect('/quiz')


@app.route('/set_performance', methods=['POST'])
def set_performance():
    """Set the performance level (affects speed and resource usage)"""
    data = request.json
    performance_level = data.get('performance_level', 'medium')  # 'low', 'medium', 'high', 'ultra'
    
    try:
        # Map performance levels to max_tokens and num_ctx
        # Lower values = faster, less memory, shorter responses
        performance_configs = {
            'low': {'max_tokens': 1024, 'num_ctx': 2048},      # Fast, minimal resources
            'medium': {'max_tokens': 1024, 'num_ctx': 4096},  # Balanced (default)
            'high': {'max_tokens': 2048, 'num_ctx': 6144},    # Slower, more resources
            'ultra': {'max_tokens': 4096, 'num_ctx': 8192}    # Slowest, maximum resources
        }
        
        if performance_level not in performance_configs:
            return jsonify({'error': 'Performance level must be: low, medium, high, or ultra'}), 400
        
        config = performance_configs[performance_level]
        rag_chain.set_performance(max_tokens=config['max_tokens'], num_ctx=config['num_ctx'])
        
        return jsonify({
            'success': True,
            'performance_level': performance_level,
            'max_tokens': rag_chain.max_tokens,
            'num_ctx': rag_chain.num_ctx,
            'message': f'Performance set to: {performance_level} (max_tokens={rag_chain.max_tokens}, num_ctx={rag_chain.num_ctx})'
        })
    except (ValueError, TypeError) as e:
        return jsonify({'error': 'Invalid performance value'}), 400

@app.route('/get_performance', methods=['GET'])
def get_performance():
    """Get the current performance settings"""
    return jsonify({
        'max_tokens': rag_chain.max_tokens,
        'num_ctx': rag_chain.num_ctx
    })

@app.route('/switch_model', methods=['POST'])
def switch_model():
    """Switch to a different model"""
    data = request.json
    model_name = data.get('model_name', '').strip().lower()
    
    # Valid model names
    valid_models = ['smollm2:360m', 'smollfinetuned']
    
    if not model_name:
        return jsonify({'error': 'Model name is required'}), 400
    
    if model_name not in valid_models:
        return jsonify({
            'error': f'Invalid model name. Must be one of: {", ".join(valid_models)}'
        }), 400
    
    try:
        rag_chain.switch_model(model_name)
        return jsonify({
            'success': True,
            'model_name': model_name,
            'message': f'Switched to model: {model_name}'
        })
    except Exception as e:
        return jsonify({'error': f'Failed to switch model: {str(e)}'}), 500

@app.route('/get_model', methods=['GET'])
def get_model():
    """Get the current model name"""
    return jsonify({
        'model_name': rag_chain.model_name
    })

@app.route('/logs', methods=['GET'])
def get_logs():
    """Get logs with optional filtering"""
    log_type = request.args.get('type', None)  # 'chat', 'question_generation', 'answer_evaluation'
    model = request.args.get('model', None)  # 'gemma'
    limit = int(request.args.get('limit', 100))
    
    logs = logger.get_logs(log_type=log_type, model=model, limit=limit)
    return jsonify({'logs': logs, 'count': len(logs)})

@app.route('/logs/stats', methods=['GET'])
def get_log_stats():
    """Get statistics about logged interactions"""
    stats = logger.get_statistics()
    return jsonify(stats)

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/teaching')
def teaching():
    return render_template('teaching.html')

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

@app.route('/generate_question', methods=['POST'])
def generate_question():
    data = request.json
    topic = data.get('topic', '').strip()
    max_tokens = data.get('max_tokens', None)
    num_ctx = data.get('num_ctx', None)
    
    # Update performance parameters if provided
    if max_tokens is not None or num_ctx is not None:
        try:
            rag_chain.set_performance(max_tokens=max_tokens, num_ctx=num_ctx)
        except (ValueError, TypeError):
            pass  # Ignore invalid values
    
    try:
        # Start timing
        start_time = time.time()
        
        # Helper function to clean context
        def clean_context(context_text):
            """Clean and filter context to remove URLs, headers, and excessive formatting"""
            if not context_text:
                return ""
            
            lines = context_text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                if line.startswith('URL:') or line.startswith('http'):
                    continue
                if line.strip().startswith('===') or line.strip().startswith('==='):
                    continue
                if not cleaned_lines and not line.strip():
                    continue
                cleaned_lines.append(line)
            
            cleaned = '\n'.join(cleaned_lines).strip()
            if len(cleaned) > 500:
                cleaned = cleaned[:500]
                last_period = cleaned.rfind('.')
                if last_period > 400:
                    cleaned = cleaned[:last_period + 1]
            
            return cleaned
        
        # Retrieve relevant course material - reduced top_k
        # Skip RAG for smollm2:360m
        if rag_chain.model_name == "smollm2:360m":
            context = ""
        else:
            if topic:
                top_k = 1  # Reduced from 3 to 1
                retrieved_docs = rag_chain.retrieve(topic, top_k=top_k)
            else:
                top_k = 1  # Reduced from 3 to 1
                query_variations = [
                    "course material",
                    "key topics",
                    "important concepts",
                    "learning material"
                ]
                query = random.choice(query_variations)
                retrieved_docs = rag_chain.retrieve(query, top_k=top_k)
            
            context = "\n".join(retrieved_docs) if retrieved_docs else ""
            context = clean_context(context)  # Clean the context
        
        # Vary question types and styles for diversity
        question_styles = [
            "application-based question",
            "problem-solving question",
        ]
        question_approaches = [
            "requires students to calculate",
            "requires students to apply",
        ]
        
        selected_style = random.choice(question_styles)
        selected_approach = random.choice(question_approaches)
        
        # Generate a question based on the context with variation
        prompt = f"""Based on the following course material, generate a single, clear, and specific {selected_style} that {selected_approach} the key concepts.

Course Material:
{context}

Generate a question that:
1. Tests understanding of important concepts from the material
2. Is clear and specific
3. Can be answered in a few sentences
4. Does not include the answer
5. Is different from questions you might have generated before (vary the wording and focus)

Make sure the question is unique and tests a different aspect or uses different wording than typical questions.

Question:"""
        
        # Temporarily increase temperature for more variation in question generation
        # Save original temperature if it exists
        original_temp = getattr(rag_chain.ollama, 'temperature', None)
        
        # Use current settings for question generation (slightly higher temperature for variation)
        from langchain_community.llms import Ollama
        question_temp = min(0.7, rag_chain.temperature + 0.2)  # Slightly higher for variation, but cap at 0.7
        question_model = Ollama(
            model=rag_chain.model_name, 
            temperature=question_temp,
            num_predict=rag_chain.max_tokens,
            num_ctx=rag_chain.num_ctx
        )
        
        response = question_model.invoke(prompt)
        question_text = response.strip()
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Determine performance level for logging
        performance_level = get_performance_level(rag_chain.max_tokens, rag_chain.num_ctx)
        
        # Log the generated question with execution time
        logger.log_question_generation(topic, question_text, rag_chain.model_name, context, performance_level, execution_time)
        
        return jsonify({
            'question': question_text,
            'context': context  # Store context for later evaluation
        })
    except Exception as e:
        import traceback
        print(f"Error generating question: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    context = data.get('context', '')
    max_tokens = data.get('max_tokens', None)
    num_ctx = data.get('num_ctx', None)
    
    if not question or not answer:
        return jsonify({'error': 'Question and answer are required'}), 400
    
    # Update performance parameters if provided
    if max_tokens is not None or num_ctx is not None:
        try:
            rag_chain.set_performance(max_tokens=max_tokens, num_ctx=num_ctx)
        except (ValueError, TypeError):
            pass  # Ignore invalid values
    
    try:
        # Start timing
        start_time = time.time()
        
        # Helper function to clean context (if not already cleaned)
        def clean_context(context_text):
            """Clean and filter context to remove URLs, headers, and excessive formatting"""
            if not context_text:
                return ""
            
            lines = context_text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                if line.startswith('URL:') or line.startswith('http'):
                    continue
                if line.strip().startswith('===') or line.strip().startswith('==='):
                    continue
                if not cleaned_lines and not line.strip():
                    continue
                cleaned_lines.append(line)
            
            cleaned = '\n'.join(cleaned_lines).strip()
            if len(cleaned) > 500:
                cleaned = cleaned[:500]
                last_period = cleaned.rfind('.')
                if last_period > 400:
                    cleaned = cleaned[:last_period + 1]
            
            return cleaned
        
        # Retrieve context only if not using smollm2:360m
        if rag_chain.model_name != "smollm2:360m":
            # Clean context if provided
            context = clean_context(context) if context else ""
        else:
            context = ""
        
        # Restructured prompt: context after task, with clear instructions
        if context:
            evaluation_prompt = f"""You are a teacher evaluating a student's answer. Provide clear, concise feedback.

Question: {question}

Student's Answer: {answer}

IMPORTANT INSTRUCTIONS:
- Write clear, concise feedback (2-3 sentences maximum)
- Use simple, direct language
- Focus on what the student did well and what needs improvement
- If the answer is incorrect, briefly explain what the correct answer should include
- DO NOT copy or paraphrase from any reference material
- Write in your own clear, conversational style

Reference Material (for accuracy only - do not copy from this):
{context}

Provide your feedback now:"""
        else:
            evaluation_prompt = f"""You are a teacher evaluating a student's answer. Provide clear, concise feedback.

Question: {question}

Student's Answer: {answer}

IMPORTANT INSTRUCTIONS:
- Write clear, concise feedback (2-3 sentences maximum)
- Use simple, direct language
- Focus on what the student did well and what needs improvement
- If the answer is incorrect, briefly explain what the correct answer should include
- Write in your own clear, conversational style

Provide your feedback now:"""
        
        response = rag_chain.ollama.invoke(evaluation_prompt)
        
        # Parse the response - remove "EXPLANATION:" prefix if present
        explanation = response
        if "EXPLANATION:" in response:
            explanation = response.split("EXPLANATION:", 1)[1].strip()
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Determine performance level for logging
        performance_level = get_performance_level(rag_chain.max_tokens, rag_chain.num_ctx)
        
        # Log the answer evaluation with execution time
        logger.log_answer_evaluation(question, answer, explanation, rag_chain.model_name, context, performance_level, execution_time)
        
        return jsonify({
            'explanation': explanation
        })
    except Exception as e:
        import traceback
        print(f"Error evaluating answer: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_teaching_material', methods=['POST'])
def generate_teaching_material():
    data = request.json
    topic = data.get('topic', '').strip()
    max_tokens = data.get('max_tokens', None)
    num_ctx = data.get('num_ctx', None)
    
    if not topic:
        return jsonify({'error': 'Topic is required'}), 400
    
    # Update performance parameters if provided
    if max_tokens is not None or num_ctx is not None:
        try:
            rag_chain.set_performance(max_tokens=max_tokens, num_ctx=num_ctx)
        except (ValueError, TypeError):
            pass  # Ignore invalid values
    
    try:
        # Start timing
        start_time = time.time()
        
        # Helper function to clean context
        def clean_context(context_text):
            """Clean and filter context to remove URLs, headers, and excessive formatting"""
            if not context_text:
                return ""
            
            lines = context_text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                if line.startswith('URL:') or line.startswith('http'):
                    continue
                if line.strip().startswith('===') or line.strip().startswith('==='):
                    continue
                if not cleaned_lines and not line.strip():
                    continue
                cleaned_lines.append(line)
            
            cleaned = '\n'.join(cleaned_lines).strip()
            if len(cleaned) > 600:
                cleaned = cleaned[:600]
                last_period = cleaned.rfind('.')
                if last_period > 450:
                    cleaned = cleaned[:last_period + 1]
            
            return cleaned
        
        # Retrieve relevant course material for the topic - reduced top_k
        # Skip RAG for smollm2:360m
        if rag_chain.model_name == "smollm2:360m":
            context = ""
        else:
            top_k = 2  # Reduced from 3 to 2 (teaching material can use slightly more)
            retrieved_docs = rag_chain.retrieve(topic, top_k=top_k)
            context = "\n".join(retrieved_docs) if retrieved_docs else ""
            context = clean_context(context)  # Clean the context
        
        # Restructured prompt: context after task, with clear instructions
        if context:
            prompt = f"""You are an experienced university-level computer science instructor specializing in Algorithms and Data Structures. Create comprehensive teaching material on {topic}.

IMPORTANT INSTRUCTIONS:
- Write clear, well-structured educational content
- Use simple, direct language that is easy to follow
- Create your own original teaching material - DO NOT copy or paraphrase from reference material
- Write in your own clear, accessible teaching style
- CRITICAL: DO NOT repeat the same content, code blocks, explanations, or phrases multiple times
- Each section should be unique - never copy-paste or repeat previous sections
- If you find yourself repeating content, STOP and move to the next section
- Keep content focused and avoid any form of repetition
- Include explicit learning objectives at the start
- Connect to future topics and applications (feed-forward orientation)

Reference Material (for accuracy only - do not copy from this):
{context}

Create detailed teaching material that covers the following:

1. **Introduction and Definition**: Clearly define {topic} and explain its purpose in computer science.

2. **Key Concepts and Theory**: 
   - Explain the fundamental principles and theoretical foundations
   - Describe how it works conceptually
   - Include any important properties or characteristics

3. **Algorithm/Implementation Details**:
   - Provide step-by-step algorithmic explanation
   - Include pseudocode that clearly shows the logic
   - Explain each step in detail

4. **Code Examples**:
   - Provide working code implementation in Python (or relevant language)
   - Include comments explaining key parts
   - Use clear, idiomatic code that follows best practices
   - If applicable, show example usage with sample input/output

5. **Complexity Analysis**:
   - **Time Complexity**: Analyze using Big-O notation (O, Θ, Ω)
     - Best case, average case, and worst case if applicable
     - Explain the derivation briefly
   - **Space Complexity**: Analyze memory usage using Big-O notation
   - Discuss trade-offs between time and space complexity when relevant

6. **Properties and Characteristics**:
   - Discuss important properties (e.g., stability for sorting, completeness for search)
   - Compare advantages and disadvantages
   - Mention any constraints or prerequisites

7. **Practical Applications**:
   - Real-world use cases
   - When to use this algorithm/data structure
   - Common scenarios where it appears in software development

8. **Related Concepts** (if applicable):
   - Briefly compare to similar algorithms/data structures
   - Explain when one might be preferred over another

**Formatting Requirements**:
- Use markdown formatting with clear headings (##, ###)
- Structure content logically with sections and subsections
- Use code blocks for pseudocode and code examples
- Make the material suitable for undergraduate computer science students

**Output**: Write the teaching material directly. Start with a title, then provide all sections above. Do not include introductory phrases like "Here is the teaching material:" - just write the content directly.

**CRITICAL**: Once you have covered all sections, STOP immediately. Do not repeat any content, code examples, or explanations. Each section should appear only once. If you complete all sections, end the material there - do not continue generating repetitive content.

Teaching Material on {topic}:
"""
        else:
            prompt = f"""You are an experienced university-level computer science instructor specializing in Algorithms and Data Structures. Create comprehensive teaching material on {topic}.

IMPORTANT INSTRUCTIONS:
- Write clear, well-structured educational content
- Use simple, direct language that is easy to follow
- Write in your own clear, accessible teaching style
- CRITICAL: DO NOT repeat the same content, code blocks, explanations, or phrases multiple times
- Each section should be unique - never copy-paste or repeat previous sections
- If you find yourself repeating content, STOP and move to the next section
- Keep content focused and avoid any form of repetition
- Include explicit learning objectives at the start
- Connect to future topics and applications (feed-forward orientation)

Create detailed teaching material that covers the following:

1. **Introduction and Definition**: Clearly define {topic} and explain its purpose in computer science.

2. **Key Concepts and Theory**: 
   - Explain the fundamental principles and theoretical foundations
   - Describe how it works conceptually
   - Include any important properties or characteristics

3. **Algorithm/Implementation Details**:
   - Provide step-by-step algorithmic explanation
   - Include pseudocode that clearly shows the logic
   - Explain each step in detail

4. **Code Examples**:
   - Provide working code implementation in Python (or relevant language)
   - Include comments explaining key parts
   - Use clear, idiomatic code that follows best practices
   - If applicable, show example usage with sample input/output

5. **Complexity Analysis**:
   - **Time Complexity**: Analyze using Big-O notation (O, Θ, Ω)
     - Best case, average case, and worst case if applicable
     - Explain the derivation briefly
   - **Space Complexity**: Analyze memory usage using Big-O notation
   - Discuss trade-offs between time and space complexity when relevant

6. **Properties and Characteristics**:
   - Discuss important properties (e.g., stability for sorting, completeness for search)
   - Compare advantages and disadvantages
   - Mention any constraints or prerequisites

7. **Practical Applications**:
   - Real-world use cases
   - When to use this algorithm/data structure
   - Common scenarios where it appears in software development

8. **Related Concepts** (if applicable):
   - Briefly compare to similar algorithms/data structures
   - Explain when one might be preferred over another

**Formatting Requirements**:
- Use markdown formatting with clear headings (##, ###)
- Structure content logically with sections and subsections
- Use code blocks for pseudocode and code examples
- Make the material suitable for undergraduate computer science students

**Output**: Write the teaching material directly. Start with a title, then provide all sections above. Do not include introductory phrases like "Here is the teaching material:" - just write the content directly.

**CRITICAL**: Once you have covered all sections, STOP immediately. Do not repeat any content, code examples, or explanations. Each section should appear only once. If you complete all sections, end the material there - do not continue generating repetitive content.

Teaching Material on {topic}:
"""
        
        # Use current settings for teaching material generation
        from langchain_community.llms import Ollama
        teaching_model = Ollama(
            model=rag_chain.model_name, 
            temperature=rag_chain.temperature,
            num_predict=rag_chain.max_tokens,
            num_ctx=rag_chain.num_ctx,
            repeat_penalty=1.3,  # Penalize repetition (1.0 = no penalty, higher = more penalty)
            repeat_last_n=128  # Look back 128 tokens for repetition detection
        )
        
        response = teaching_model.invoke(prompt)
        material_text = response.strip()
        
        # Post-process to remove repetitive content
        material_text = remove_repetitive_content(material_text)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Determine performance level for logging
        performance_level = get_performance_level(rag_chain.max_tokens, rag_chain.num_ctx)
        
        # Log the generated teaching material with execution time
        logger.log_teaching_material(topic, material_text, rag_chain.model_name, context, performance_level, execution_time)
        
        return jsonify({
            'material': material_text,
            'topic': topic,
            'context': context  # Include context for reference
        })
    except Exception as e:
        import traceback
        print(f"Error generating teaching material: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

# Consistent questions for feedback experimentation
FEEDBACK_QUESTIONS = [
    {
        "id": "q1",
        "topic": "binary search",
        "question": "Explain how binary search works and what its time complexity is."
    },
    {
        "id": "q2",
        "topic": "merge sort",
        "question": "Describe the merge sort algorithm and analyze its time and space complexity."
    },
    {
        "id": "q3",
        "topic": "hash tables",
        "question": "What is a hash table and what are its main advantages?"
    },
    {
        "id": "q4",
        "topic": "time complexity",
        "question": "What is the time complexity of finding an element in an unsorted array?"
    },
    {
        "id": "q5",
        "topic": "binary trees",
        "question": "Explain the difference between a binary tree and a binary search tree."
    }
]

@app.route('/get_feedback_questions', methods=['GET'])
def get_feedback_questions():
    """Get the list of consistent questions for feedback experimentation"""
    return jsonify({
        'questions': FEEDBACK_QUESTIONS,
        'total': len(FEEDBACK_QUESTIONS)
    })

@app.route('/submit_feedback_answer', methods=['POST'])
def submit_feedback_answer():
    """Submit an answer for a feedback question and get model feedback"""
    data = request.json
    question_id = data.get('question_id', '').strip()
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    topic = data.get('topic', '').strip()
    max_tokens = data.get('max_tokens', None)
    num_ctx = data.get('num_ctx', None)
    
    if not question or not answer:
        return jsonify({'error': 'Question and answer are required'}), 400
    
    # Update performance parameters if provided
    if max_tokens is not None or num_ctx is not None:
        try:
            rag_chain.set_performance(max_tokens=max_tokens, num_ctx=num_ctx)
        except (ValueError, TypeError):
            pass  # Ignore invalid values
    
    try:
        # Start timing
        start_time = time.time()
        
        # Helper function to clean context
        def clean_context(context_text):
            """Clean and filter context to remove URLs, headers, and excessive formatting"""
            if not context_text:
                return ""
            
            lines = context_text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                if line.startswith('URL:') or line.startswith('http'):
                    continue
                if line.strip().startswith('===') or line.strip().startswith('==='):
                    continue
                if not cleaned_lines and not line.strip():
                    continue
                cleaned_lines.append(line)
            
            cleaned = '\n'.join(cleaned_lines).strip()
            if len(cleaned) > 500:
                cleaned = cleaned[:500]
                last_period = cleaned.rfind('.')
                if last_period > 400:
                    cleaned = cleaned[:last_period + 1]
            
            return cleaned
        
        # Retrieve relevant context for the topic
        # Skip RAG for smollm2:360m
        context = ""
        if rag_chain.model_name != "smollm2:360m" and topic:
            try:
                top_k = 1
                retrieved_docs = rag_chain.retrieve(topic, top_k=top_k)
                context = "\n".join(retrieved_docs) if retrieved_docs else ""
                context = clean_context(context)
            except Exception as e:
                print(f"Error retrieving context: {e}")
                context = ""
        
        # Use the same evaluation prompt as submit_answer
        if context:
            evaluation_prompt = f"""You are a teacher evaluating a student's answer. Provide clear, concise feedback.

Question: {question}

Student's Answer: {answer}

IMPORTANT INSTRUCTIONS:
- Write clear, concise feedback (2-3 sentences maximum)
- Use simple, direct language
- Focus on what the student did well and what needs improvement
- If the answer is incorrect, briefly explain what the correct answer should include
- DO NOT copy or paraphrase from any reference material
- Write in your own clear, conversational style

Reference Material (for accuracy only - do not copy from this):
{context}

Provide your feedback now:"""
        else:
            evaluation_prompt = f"""You are a teacher evaluating a student's answer. Provide clear, concise feedback.

Question: {question}

Student's Answer: {answer}

IMPORTANT INSTRUCTIONS:
- Write clear, concise feedback (2-3 sentences maximum)
- Use simple, direct language
- Focus on what the student did well and what needs improvement
- If the answer is incorrect, briefly explain what the correct answer should include
- Write in your own clear, conversational style

Provide your feedback now:"""
        
        response = rag_chain.ollama.invoke(evaluation_prompt)
        
        # Parse the response - remove "EXPLANATION:" prefix if present
        feedback = response
        if "EXPLANATION:" in response:
            feedback = response.split("EXPLANATION:", 1)[1].strip()
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Determine performance level for logging
        performance_level = get_performance_level(rag_chain.max_tokens, rag_chain.num_ctx)
        
        # Log the answer evaluation with execution time
        logger.log_answer_evaluation(question, answer, feedback, rag_chain.model_name, context, performance_level, execution_time)
        
        return jsonify({
            'feedback': feedback,
            'question_id': question_id,
            'execution_time': execution_time
        })
    except Exception as e:
        import traceback
        print(f"Error evaluating answer: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Get port from environment variable (Railway provides this)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)