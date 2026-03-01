# Web Application - RAG Interface

A Flask web application for educational content generation using SmollM2 models with optional RAG (Retrieval-Augmented Generation).

## Features

- **Quiz Generation**: Generate questions based on course material
- **Teaching Material**: Create comprehensive teaching content on various topics
- **Feedback Experimentation**: Consistent questions for human experimentation with model feedback
- **Model Support**: 
  - `smollm2:360m` - Base model (no RAG)
  - `smollfinetuned` - Finetuned model (with RAG)

## Requirements

- Python 3.8+
- Ollama installed and running
- Models available in Ollama:
  - `smollm2:360m`
  - `smollfinetuned`

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install and start Ollama:
   - Download from: https://ollama.ai
   - Ensure Ollama is running: `ollama serve` (usually runs automatically)

3. Setup models automatically:
```bash
# Windows
python setup_models.py

# Linux/Mac
python setup_models.py
```

This script will:
- Pull the base `smollm2:360m` model from Ollama registry
- Create the `smollfinetuned` model from the bundled GGUF file in `models/`

**Note**: The finetuned model (676MB) is included in the `models/` directory, making this a self-contained deployment.

## Running the Application

1. Start the Flask application:
```bash
python app.py
```

2. Access the web interface at:
   - http://localhost:5000

## Project Structure

```
webapp/
├── app.py                 # Main Flask application
├── rag_chain.py           # RAG chain implementation
├── model_logger.py       # Logging functionality
├── requirements.txt      # Python dependencies
├── setup_models.py       # Model setup script
├── setup_models.bat      # Windows model setup script
├── models/               # Bundled model files
│   ├── smollm2-360m-lora-finetuned-merged-f16.gguf  # Finetuned model (676MB)
│   └── Modelfile         # Ollama Modelfile for finetuned model
├── templates/           # HTML templates
│   ├── base.html
│   ├── quiz.html
│   ├── teaching.html
│   ├── feedback.html
│   └── includes/        # Reusable template components
│       ├── header.html
│       ├── navigation.html
│       ├── model_controls.html
│       └── performance_controls.html
├── static/              # Static assets
│   └── css/
│       ├── style.css
│       ├── quiz.css
│       ├── quiz.js
│       ├── teaching.css
│       ├── teaching.js
│       ├── feedback.css
│       └── feedback.js
├── logs/                # Application logs (created automatically)
└── chroma_db/           # ChromaDB database (created automatically)
```

## Configuration

- Default port: 5000 (can be set via `PORT` environment variable)
- Default model: `smollm2:360m`
- Performance levels: Low, Medium, High, Ultra

## Notes

- The `smollm2:360m` model does not use RAG (no context retrieval)
- The `smollfinetuned` model uses RAG for enhanced context
- Logs are stored in JSONL format in the `logs/` directory
- ChromaDB is used for RAG functionality (only for `smollfinetuned`)

## API Endpoints

- `GET /` - Redirects to `/quiz`
- `GET /quiz` - Quiz page
- `GET /teaching` - Teaching material page
- `GET /feedback` - Feedback experimentation page
- `POST /generate_question` - Generate a quiz question
- `POST /submit_answer` - Submit answer and get feedback
- `POST /generate_teaching_material` - Generate teaching material
- `POST /get_feedback_questions` - Get list of feedback questions
- `POST /submit_feedback_answer` - Submit feedback answer
- `POST /switch_model` - Switch between models
- `POST /set_performance` - Set performance level
- `GET /get_model` - Get current model
- `GET /get_performance` - Get current performance settings
- `GET /logs` - Get application logs
- `GET /logs/stats` - Get log statistics
