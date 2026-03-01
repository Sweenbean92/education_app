#!/bin/bash
echo "Starting Flask Web Application..."
echo ""
echo "Make sure Ollama is running and models are available:"
echo "  - smollm2:360m"
echo "  - smollfinetuned"
echo ""
python3 app.py
