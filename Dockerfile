# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for Ollama and the application
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Add Ollama to PATH
ENV PATH="/usr/local/bin:${PATH}"

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p logs chroma_db

# Set up models (this will pull base model and create finetuned model)
RUN python setup_models.py || echo "Model setup completed with warnings"

# Populate ChromaDB with documents from docs/ folder (if docs exist)
# This downloads the embedding model and processes all .txt files
RUN if [ -d "docs" ] && [ "$(ls -A docs/*.txt 2>/dev/null)" ]; then \
        echo "Populating ChromaDB with documents from docs/ folder..." && \
        python chroma_db.py || echo "Database population completed with warnings"; \
    else \
        echo "No docs folder or .txt files found, skipping database population"; \
    fi

# Expose the application port
EXPOSE 5000

# Set environment variables
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

# Create a startup script that runs Ollama in background and then starts Flask
RUN echo '#!/bin/bash\n\
set -e\n\
# Start Ollama in the background\n\
echo "Starting Ollama server..."\n\
ollama serve &\n\
OLLAMA_PID=$!\n\
# Wait for Ollama to be ready (poll until it responds)\n\
echo "Waiting for Ollama to be ready..."\n\
for i in {1..30}; do\n\
  if ollama list >/dev/null 2>&1; then\n\
    echo "Ollama is ready!"\n\
    break\n\
  fi\n\
  if [ $i -eq 30 ]; then\n\
    echo "Ollama failed to start after 30 attempts"\n\
    exit 1\n\
  fi\n\
  sleep 1\n\
done\n\
# Start Flask application\n\
echo "Starting Flask application..."\n\
exec python app.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Use the startup script
CMD ["/app/start.sh"]
