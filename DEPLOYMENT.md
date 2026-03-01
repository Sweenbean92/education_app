# Deployment Guide

This guide explains how to deploy the web application with the bundled finetuned model.

## Self-Contained Deployment

The application includes the finetuned model (676MB GGUF file) in the `models/` directory, making it a **self-contained deployment**. This means:

✅ **No external model downloads required** (except base model from Ollama registry)  
✅ **Works offline** after initial setup  
✅ **Consistent model version** across deployments  
✅ **Easy to package and distribute**

## Deployment Steps

### 1. Package the Application

The `webapp/` directory contains everything needed:
- Application code
- Templates and static files
- **Bundled finetuned model** (`models/smollm2-360m-lora-finetuned-merged-f16.gguf`)
- Setup scripts

### 2. Install Dependencies

On the target system:
```bash
cd webapp
pip install -r requirements.txt
```

### 3. Install Ollama

Download and install Ollama from: https://ollama.ai

Ensure Ollama is running:
```bash
ollama serve
```

### 4. Setup Models

Run the setup script to configure models:
```bash
python setup_models.py
```

This will:
- Pull `smollm2:360m` from Ollama registry (if not already present)
- Create `smollfinetuned` model from the bundled GGUF file

### 5. Uninstalling Models (Optional)

To remove the models from Ollama:
```bash
python uninstall_models.py
```

This will:
- Remove `smollfinetuned` model (always)
- Optionally remove `smollm2:360m` (with confirmation)

**Note**: The bundled GGUF file is NOT deleted. You can recreate models by running `setup_models.py` again.

### 5. Run the Application

```bash
python app.py
```

## Model Files

### Included Model
- **File**: `models/smollm2-360m-lora-finetuned-merged-f16.gguf`
- **Size**: ~676MB
- **Format**: GGUF (Ollama-compatible)
- **Usage**: Automatically set up by `setup_models.py`

### Base Model
- **Name**: `smollm2:360m`
- **Source**: Ollama registry (downloaded automatically)
- **Size**: ~360MB (downloaded on first setup)

## Deployment Options

### Option 1: Local Deployment
- Copy `webapp/` directory to target machine
- Run setup and start application
- Access at `http://localhost:5000`

### Option 2: Docker Deployment

The project includes a `Dockerfile` and `docker-compose.yml` for easy containerized deployment.

#### Using Docker Compose (Recommended)

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

2. View logs:
```bash
docker-compose logs -f
```

3. Stop the application:
```bash
docker-compose down
```

#### Using Docker directly

1. Build the Docker image:
```bash
docker build -t webapp .
```

2. Run the container:
```bash
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/logs:/app/logs \
  --name webapp \
  webapp
```

3. View logs:
```bash
docker logs -f webapp
```

4. Stop the container:
```bash
docker stop webapp
docker rm webapp
```

**Note**: The Dockerfile automatically:
- Installs Ollama
- Sets up both models during build
- Starts Ollama server in the background
- Runs the Flask application

**Resource Requirements**: 
- Minimum: 4GB RAM, 2 CPU cores
- Recommended: 8GB RAM, 4 CPU cores

### Option 3: Cloud Deployment
- Upload `webapp/` directory to cloud server
- Install Ollama on server
- Run setup scripts
- Use process manager (systemd, PM2, etc.) to keep app running

## Model Storage

The bundled model is stored in:
- **Location**: `webapp/models/smollm2-360m-lora-finetuned-merged-f16.gguf`
- **Ollama Storage**: After setup, Ollama creates its own copy
- **Disk Space**: ~1.3GB total (GGUF file + Ollama's copy)

## Troubleshooting

### Model Not Found
If `setup_models.py` fails:
1. Check Ollama is running: `ollama list`
2. Verify GGUF file exists: `ls models/*.gguf`
3. Check Modelfile path is correct
4. Try creating model manually:
   ```bash
   cd models
   ollama create smollfinetuned -f Modelfile
   ```

### Large File Size
The GGUF file is ~676MB. For deployments with size constraints:
- Consider using a lower quantization (Q4, Q5) to reduce size
- Use external storage and symlink the model file
- Exclude from version control (already in `.gitignore`)

### Port Configuration
Default port is 5000. Change via environment variable:
```bash
export PORT=8080
python app.py
```

## Notes

- The finetuned model is **bundled** with the application
- No internet connection needed after initial setup (except for base model)
- Model setup only needs to run once per deployment
- Both models are required for full functionality
