// Performance control state
let currentPerformanceLevel = 'medium'; // Default performance level
let currentMaxTokens = 1024;
let currentNumCtx = 4096;
let currentModel = 'smollm2:360m'; // Default model

// Switch model
async function switchModel(modelName) {
    try {
        const response = await fetch('/switch_model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model_name: modelName
            })
        });
        
        const data = await response.json();
        if (response.ok) {
            currentModel = modelName;
            console.log(`Switched to model: ${modelName}`);
        } else {
            console.error('Error switching model:', data.error);
            alert(`Error switching model: ${data.error || 'Unknown error'}`);
            // Reset select to current model
            const select = document.getElementById('model-select');
            if (select) {
                select.value = currentModel;
            }
        }
    } catch (error) {
        console.error('Error switching model:', error);
        alert('Error: Could not connect to server');
        // Reset select to current model
        const select = document.getElementById('model-select');
        if (select) {
            select.value = currentModel;
        }
    }
}

// Get current model from backend
async function getModel() {
    try {
        const response = await fetch('/get_model');
        const data = await response.json();
        if (data.model_name) {
            currentModel = data.model_name;
            const select = document.getElementById('model-select');
            if (select) {
                select.value = currentModel;
            }
        }
    } catch (error) {
        console.error('Error getting model:', error);
    }
}

// Update performance level
function updatePerformance(performanceLevel) {
    currentPerformanceLevel = performanceLevel;
    setPerformance(performanceLevel);
}

// Set performance on backend
async function setPerformance(performanceLevel) {
    try {
        const response = await fetch('/set_performance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                performance_level: performanceLevel
            })
        });
        
        const data = await response.json();
        if (response.ok && data.max_tokens && data.num_ctx) {
            currentMaxTokens = data.max_tokens;
            currentNumCtx = data.num_ctx;
        }
    } catch (error) {
        console.error('Error setting performance:', error);
    }
}

// Get current performance from backend
async function getPerformance() {
    try {
        const response = await fetch('/get_performance');
        const data = await response.json();
        if (data.max_tokens && data.num_ctx) {
            currentMaxTokens = data.max_tokens;
            currentNumCtx = data.num_ctx;
            
            // Determine performance level based on values
            const select = document.getElementById('performance-select');
            if (select) {
                if (data.max_tokens <= 512 && data.num_ctx <= 2048) {
                    select.value = 'low';
                    currentPerformanceLevel = 'low';
                } else if (data.max_tokens <= 1024 && data.num_ctx <= 4096) {
                    select.value = 'medium';
                    currentPerformanceLevel = 'medium';
                } else if (data.max_tokens <= 2048 && data.num_ctx <= 6144) {
                    select.value = 'high';
                    currentPerformanceLevel = 'high';
                } else {
                    select.value = 'ultra';
                    currentPerformanceLevel = 'ultra';
                }
            }
        }
    } catch (error) {
        console.error('Error getting performance:', error);
    }
}

async function generateQuestion() {
    const topic = document.getElementById('topic-input').value.trim();
    const generateBtn = document.getElementById('generate-btn');
    const quizContent = document.getElementById('quiz-content');
    
    // Disable button
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating...';
    
    // Clear previous content
    quizContent.innerHTML = '<div class="loading-message">Generating question...</div>';
    
    try {
        const response = await fetch('/generate_question', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                topic: topic,
                max_tokens: currentMaxTokens,
                num_ctx: currentNumCtx
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentQuestion = data.question;
            currentContext = data.context;
            
            // Display question
            displayQuestion(data.question);
        } else {
            quizContent.innerHTML = `<div class="error-message">Error: ${data.error || 'Failed to generate question'}</div>`;
        }
    } catch (error) {
        quizContent.innerHTML = `<div class="error-message">Error: Could not connect to server</div>`;
        console.error('Error:', error);
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Question';
    }
}

function displayQuestion(question) {
    const quizContent = document.getElementById('quiz-content');
    
    // Render markdown if available (in case question contains markdown)
    let questionHtml = question;
    if (typeof marked !== 'undefined') {
        questionHtml = marked.parse(question);
    } else {
        questionHtml = escapeHtml(question);
    }
    
    const questionSectionHtml = `
        <div class="question-section">
            <h2>Question</h2>
            <div class="question-text">${questionHtml}</div>
        </div>
        <div class="answer-section">
            <h3>Your Answer</h3>
            <textarea id="answer-input" 
                      placeholder="Type your answer here..." 
                      rows="6"></textarea>
            <button id="submit-btn" class="btn-primary" onclick="submitAnswer()">
                Submit Answer
            </button>
        </div>
        <div id="feedback-section" class="feedback-section" style="display: none;"></div>
    `;
    
    quizContent.innerHTML = questionSectionHtml;
    
    // Focus on answer input
    document.getElementById('answer-input').focus();
}

async function submitAnswer() {
    const answer = document.getElementById('answer-input').value.trim();
    const submitBtn = document.getElementById('submit-btn');
    const feedbackSection = document.getElementById('feedback-section');
    
    if (!answer) {
        alert('Please enter an answer before submitting.');
        return;
    }
    
    // Disable button
    submitBtn.disabled = true;
    submitBtn.textContent = 'Evaluating...';
    
    // Show feedback section
    feedbackSection.style.display = 'block';
    feedbackSection.innerHTML = '<div class="loading-message">Evaluating your answer...</div>';
    
    try {
        const response = await fetch('/submit_answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: currentQuestion,
                answer: answer,
                context: currentContext,
                max_tokens: currentMaxTokens,
                num_ctx: currentNumCtx
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Display feedback
            displayFeedback(data.explanation);
        } else {
            feedbackSection.innerHTML = `<div class="error-message">Error: ${data.error || 'Failed to evaluate answer'}</div>`;
        }
    } catch (error) {
        feedbackSection.innerHTML = `<div class="error-message">Error: Could not connect to server</div>`;
        console.error('Error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Answer';
    }
}

function displayFeedback(explanation) {
    const feedbackSection = document.getElementById('feedback-section');
    
    // Render markdown explanation
    let explanationHtml = explanation;
    if (typeof marked !== 'undefined') {
        explanationHtml = marked.parse(explanation);
    } else {
        explanationHtml = escapeHtml(explanation).replace(/\n/g, '<br>');
    }
    
    const feedbackHtml = `
        <h3>Feedback</h3>
        <div class="explanation">
            ${explanationHtml}
        </div>
        <div class="quiz-actions">
            <button class="btn-secondary" onclick="generateQuestion()">
                New Question
            </button>
            <button class="btn-secondary" onclick="clearQuiz()">
                Clear
            </button>
        </div>
    `;
    
    feedbackSection.innerHTML = feedbackHtml;
}

function clearQuiz() {
    const quizContent = document.getElementById('quiz-content');
    quizContent.innerHTML = `
        <div class="welcome-message">
            <p>Click "Generate Question" to start a quiz based on your course material.</p>
            <p>You can optionally specify a topic to focus the question on.</p>
        </div>
    `;
    currentQuestion = '';
    currentContext = '';
    document.getElementById('topic-input').value = '';
}


function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Allow Enter key to submit answer (with Shift+Enter for new line)
document.addEventListener('DOMContentLoaded', function() {
    // This will be set up when the answer input is created
    document.addEventListener('keydown', function(e) {
        const answerInput = document.getElementById('answer-input');
        if (answerInput && document.activeElement === answerInput) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitAnswer();
            }
        }
    });
    
    // Initialize performance control and model on page load
    getPerformance();
    getModel();
});