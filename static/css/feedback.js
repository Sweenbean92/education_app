// Global state variables
let questions = [];
let currentQuestionIndex = -1;
let questionAnswers = {}; // Store answers and feedback for each question

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

// Load questions from backend
async function loadQuestions() {
    const questionsList = document.getElementById('questions-list');
    if (!questionsList) {
        console.error('Questions list element not found');
        return;
    }
    
    try {
        questionsList.innerHTML = '<div class="loading-message">Loading questions...</div>';
        const response = await fetch('/get_feedback_questions');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Questions loaded:', data);
        
        if (data.questions && Array.isArray(data.questions)) {
            questions = data.questions;
            renderQuestionsList();
            updateProgress();
            
            // Auto-select first question if available
            if (questions.length > 0 && currentQuestionIndex < 0) {
                selectQuestion(0);
            }
        } else {
            console.error('Invalid questions data:', data);
            questionsList.innerHTML = 
                '<div class="error-message">Error: Invalid question data received</div>';
        }
    } catch (error) {
        console.error('Error loading questions:', error);
        if (questionsList) {
            questionsList.innerHTML = 
                '<div class="error-message">Error: Could not load questions. Please refresh the page.</div>';
        }
    }
}

// Render the questions list in the sidebar
function renderQuestionsList() {
    const questionsList = document.getElementById('questions-list');
    
    if (!questionsList) {
        console.error('Questions list element not found');
        return;
    }
    
    if (!questions || questions.length === 0) {
        questionsList.innerHTML = '<div class="error-message">No questions available</div>';
        return;
    }
    
    const questionsHtml = questions.map((q, index) => {
        const hasAnswer = questionAnswers[q.id] && questionAnswers[q.id].answer;
        const hasFeedback = questionAnswers[q.id] && questionAnswers[q.id].feedback;
        const isActive = currentQuestionIndex === index;
        
        let statusClass = 'question-item';
        if (isActive) statusClass += ' active';
        if (hasFeedback) statusClass += ' completed';
        else if (hasAnswer) statusClass += ' answered';
        
        return `
            <div class="${statusClass}" onclick="selectQuestion(${index})">
                <div class="question-number">${index + 1}</div>
                <div class="question-preview">
                    <div class="question-title">Question ${index + 1}</div>
                    <div class="question-topic">${q.topic}</div>
                </div>
                ${hasFeedback ? '<div class="question-status">✓</div>' : ''}
            </div>
        `;
    }).join('');
    
    questionsList.innerHTML = questionsHtml;
}

// Select a question to display
function selectQuestion(index) {
    if (!questions || questions.length === 0) {
        console.error('Questions not loaded yet');
        return;
    }
    
    if (index < 0 || index >= questions.length) {
        console.error('Invalid question index:', index);
        return;
    }
    
    currentQuestionIndex = index;
    const question = questions[index];
    
    renderQuestionsList();
    displayQuestion(question);
    updateProgress();
}

// Display the selected question
function displayQuestion(question) {
    const feedbackContent = document.getElementById('feedback-content');
    
    if (!feedbackContent) {
        console.error('Feedback content element not found');
        return;
    }
    
    if (!question || !question.question) {
        console.error('Invalid question data:', question);
        feedbackContent.innerHTML = '<div class="error-message">Invalid question data</div>';
        return;
    }
    
    // Render markdown if available
    let questionHtml = question.question;
    if (typeof marked !== 'undefined') {
        questionHtml = marked.parse(question.question);
    } else {
        questionHtml = escapeHtml(question.question);
    }
    
    // Get existing answer and feedback if available
    const existingData = questionAnswers[question.id] || {};
    const existingAnswer = existingData.answer || '';
    const existingFeedback = existingData.feedback || '';
    
    const questionSectionHtml = `
        <div class="question-section">
            <div class="question-header">
                <h2>Question ${currentQuestionIndex + 1} of ${questions.length}</h2>
                <div class="question-topic-badge">${question.topic}</div>
            </div>
            <div class="question-text">${questionHtml}</div>
        </div>
        <div class="answer-section">
            <h3>Your Answer</h3>
            <textarea id="answer-input" 
                      placeholder="Type your answer here..." 
                      rows="8">${existingAnswer}</textarea>
            <button id="submit-btn" class="btn-primary" onclick="submitAnswer()" ${existingFeedback ? 'style="display: none;"' : ''}>
                Submit Answer
            </button>
        </div>
        ${existingFeedback ? `
        <div class="feedback-section">
            <h3>Feedback</h3>
            <div class="feedback-text">${formatFeedback(existingFeedback)}</div>
            <div class="feedback-actions">
                <button class="btn-secondary" onclick="selectQuestion(${currentQuestionIndex})">
                    Review Answer
                </button>
                ${currentQuestionIndex < questions.length - 1 ? `
                <button class="btn-primary" onclick="selectQuestion(${currentQuestionIndex + 1})">
                    Next Question
                </button>
                ` : ''}
            </div>
        </div>
        ` : '<div id="feedback-section" class="feedback-section" style="display: none;"></div>'}
    `;
    
    feedbackContent.innerHTML = questionSectionHtml;
    
    // Focus on answer input if no feedback yet
    if (!existingFeedback) {
        const answerInput = document.getElementById('answer-input');
        if (answerInput) {
            answerInput.focus();
        }
    }
}

// Submit answer and get feedback
async function submitAnswer() {
    if (currentQuestionIndex < 0 || currentQuestionIndex >= questions.length) return;
    
    const question = questions[currentQuestionIndex];
    const answer = document.getElementById('answer-input').value.trim();
    const submitBtn = document.getElementById('submit-btn');
    const feedbackSection = document.getElementById('feedback-section');
    
    if (!answer) {
        alert('Please enter an answer before submitting.');
        return;
    }
    
    // Disable button
    submitBtn.disabled = true;
    submitBtn.textContent = 'Getting Feedback...';
    
    // Show feedback section
    feedbackSection.style.display = 'block';
    feedbackSection.innerHTML = '<div class="loading-message">Generating feedback...</div>';
    
    try {
        const response = await fetch('/submit_feedback_answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question_id: question.id,
                question: question.question,
                answer: answer,
                topic: question.topic,
                max_tokens: currentMaxTokens,
                num_ctx: currentNumCtx
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Store answer and feedback
            questionAnswers[question.id] = {
                answer: answer,
                feedback: data.feedback
            };
            
            // Display feedback
            displayFeedback(data.feedback);
            renderQuestionsList(); // Update sidebar to show completed status
            updateProgress();
        } else {
            feedbackSection.innerHTML = `<div class="error-message">Error: ${data.error || 'Failed to get feedback'}</div>`;
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Answer';
        }
    } catch (error) {
        feedbackSection.innerHTML = `<div class="error-message">Error: Could not connect to server</div>`;
        console.error('Error:', error);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Answer';
    }
}

// Display feedback
function displayFeedback(feedback) {
    const feedbackSection = document.getElementById('feedback-section');
    const submitBtn = document.getElementById('submit-btn');
    
    // Hide submit button
    if (submitBtn) {
        submitBtn.style.display = 'none';
    }
    
    const feedbackHtml = `
        <h3>Feedback</h3>
        <div class="feedback-text">
            ${formatFeedback(feedback)}
        </div>
        <div class="feedback-actions">
            <button class="btn-secondary" onclick="selectQuestion(${currentQuestionIndex})">
                Review Answer
            </button>
            ${currentQuestionIndex < questions.length - 1 ? `
            <button class="btn-primary" onclick="selectQuestion(${currentQuestionIndex + 1})">
                Next Question
            </button>
            ` : `
            <div class="completion-message">
                <p>You've completed all questions!</p>
            </div>
            `}
        </div>
    `;
    
    feedbackSection.innerHTML = feedbackHtml;
}

// Format feedback text (markdown support)
function formatFeedback(text) {
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    } else {
        return escapeHtml(text).replace(/\n/g, '<br>');
    }
}

// Update progress indicator
function updateProgress() {
    const progressText = document.getElementById('progress-text');
    if (progressText) {
        const completed = Object.keys(questionAnswers).filter(id => questionAnswers[id].feedback).length;
        progressText.textContent = `Progress: ${completed}/${questions.length}`;
    }
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Allow Enter key to submit answer (with Shift+Enter for new line)
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing feedback page...');
    
    // Initialize performance control and model on page load
    getPerformance();
    getModel();
    
    // Wait a bit to ensure DOM is fully ready, then load questions
    setTimeout(() => {
        loadQuestions();
    }, 100);
    
    // Set up keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        const answerInput = document.getElementById('answer-input');
        if (answerInput && document.activeElement === answerInput) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const submitBtn = document.getElementById('submit-btn');
                if (submitBtn && !submitBtn.disabled && submitBtn.style.display !== 'none') {
                    submitAnswer();
                }
            }
        }
        
        // Arrow keys for navigation
        if (e.key === 'ArrowLeft' && e.ctrlKey && currentQuestionIndex > 0) {
            e.preventDefault();
            selectQuestion(currentQuestionIndex - 1);
        } else if (e.key === 'ArrowRight' && e.ctrlKey && currentQuestionIndex < questions.length - 1) {
            e.preventDefault();
            selectQuestion(currentQuestionIndex + 1);
        }
    });
});
