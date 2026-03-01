# Models Directory

This directory contains the bundled finetuned model for self-contained deployment.

## Contents

- `smollm2-360m-lora-finetuned-merged-f16.gguf` - The finetuned model in GGUF format (~676MB)
- `Modelfile` - Ollama Modelfile configuration for the finetuned model

## Setup

The model is automatically set up when you run:
```bash
python setup_models.py
```

This creates the `smollfinetuned` model in Ollama using the bundled GGUF file.

## Manual Setup

If you need to set up the model manually:
```bash
cd models
ollama create smollfinetuned -f Modelfile
```

## File Size

The GGUF file is approximately 676MB. This is included in the deployment to ensure:
- Consistent model version across deployments
- No external downloads required
- Works offline after initial setup

## Notes

- The model file is large but necessary for the finetuned functionality
- Ollama will create its own copy after setup (~1.3GB total disk usage)
- The file is excluded from git by default (see `.gitignore`)
