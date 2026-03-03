// Performance control state (default: high)
let currentPerformanceLevel = 'high'; // Default performance level
let currentMaxTokens = 2048;
let currentNumCtx = 6144;
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
            if (data.max_tokens <= 512 && data.num_ctx <= 2048) {
                currentPerformanceLevel = 'low';
            } else if (data.max_tokens <= 1024 && data.num_ctx <= 4096) {
                currentPerformanceLevel = 'medium';
            } else if (data.max_tokens <= 2048 && data.num_ctx <= 6144) {
                currentPerformanceLevel = 'high';
            } else {
                currentPerformanceLevel = 'ultra';
            }
        }
    } catch (error) {
        console.error('Error getting performance:', error);
    }
}

// Initialize performance to high on page load
async function initializePerformance() {
    try {
        await setPerformance('high');
    } catch (error) {
        console.error('Error initializing performance:', error);
    }
}

async function generateTeachingMaterial() {
    const topic = document.getElementById('topic-input').value.trim();
    const generateBtn = document.getElementById('generate-btn');
    const teachingContent = document.getElementById('teaching-content');
    
    // Validate topic is provided
    if (!topic) {
        alert('Please enter a topic before generating teaching material.');
        return;
    }
    
    // Disable button
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating...';
    
    // Clear previous content
    teachingContent.innerHTML = '<div class="loading-message">Generating teaching material...</div>';
    
    try {
        const response = await fetch('/generate_teaching_material', {
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
            // Display teaching material
            displayTeachingMaterial(data.material, topic);
        } else {
            teachingContent.innerHTML = `<div class="error-message">Error: ${data.error || 'Failed to generate teaching material'}</div>`;
        }
    } catch (error) {
        teachingContent.innerHTML = `<div class="error-message">Error: Could not connect to server</div>`;
        console.error('Error:', error);
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Material';
    }
}

function displayTeachingMaterial(material, topic) {
    const teachingContent = document.getElementById('teaching-content');
    
    // Render markdown if available
    let materialHtml = material;
    if (typeof marked !== 'undefined') {
        materialHtml = marked.parse(material);
    } else {
        materialHtml = escapeHtml(material).replace(/\n/g, '<br>');
    }
    
    const materialSectionHtml = `
        <div class="material-section">
            <h2>Teaching Material: ${escapeHtml(topic)}</h2>
            <div class="material-content">
                ${materialHtml}
            </div>
        </div>
        <div class="teaching-actions">
            <button class="btn-secondary" onclick="clearTeachingMaterial()">
                Clear
            </button>
            <button class="btn-secondary" onclick="generateTeachingMaterial()">
                Generate New Material
            </button>
        </div>
    `;
    
    teachingContent.innerHTML = materialSectionHtml;
}

function clearTeachingMaterial() {
    const teachingContent = document.getElementById('teaching-content');
    teachingContent.innerHTML = `
        <div class="welcome-message">
            <p>Enter a topic above and click "Generate Material" to create teaching content.</p>
            <p>The content will be generated based on your course material.</p>
        </div>
    `;
    document.getElementById('topic-input').value = '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize performance to high and model on page load
document.addEventListener('DOMContentLoaded', function() {
    initializePerformance();
    getModel();
});

