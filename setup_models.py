#!/usr/bin/env python3
"""
Setup script to create Ollama models from bundled GGUF files.
This script automatically sets up the finetuned model for use with the application.
"""

import os
import subprocess
import sys
from pathlib import Path

def check_ollama_installed():
    """Check if Ollama is installed and accessible"""
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def create_model_from_modelfile(model_name, modelfile_path):
    """Create an Ollama model from a Modelfile"""
    try:
        # Change to the models directory to resolve relative paths in Modelfile
        models_dir = modelfile_path.parent
        original_dir = os.getcwd()
        
        try:
            os.chdir(models_dir)
            # Use absolute path for Modelfile to ensure it's found
            cmd = ['ollama', 'create', model_name, '-f', str(modelfile_path.resolve())]
            print(f"Creating model '{model_name}' from {modelfile_path.name}...")
            print(f"  Working directory: {os.getcwd()}")
            print(f"  Modelfile: {modelfile_path.resolve()}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print(f"✓ Successfully created model '{model_name}'")
                return True
            else:
                # Check if model already exists
                if 'already exists' in result.stderr.lower() or 'model already exists' in result.stderr.lower():
                    print(f"⚠ Model '{model_name}' already exists. Skipping...")
                    return True
                else:
                    print(f"✗ Error creating model: {result.stderr}")
                    return False
        finally:
            os.chdir(original_dir)
            
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout while creating model '{model_name}'")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_model_exists(model_name):
    """Check if a model already exists in Ollama"""
    try:
        result = subprocess.run(['ollama', 'list'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            return model_name in result.stdout
        return False
    except Exception:
        return False

def setup_base_model():
    """Setup the base smollm2:360m model"""
    print("\n=== Setting up base model: smollm2:360m ===")
    if check_model_exists('smollm2:360m'):
        print("✓ Model 'smollm2:360m' already exists")
        return True
    
    print("Pulling base model from Ollama registry...")
    try:
        result = subprocess.run(['ollama', 'pull', 'smollm2:360m'], 
                              capture_output=True, 
                              text=True, 
                              timeout=300)
        if result.returncode == 0:
            print("✓ Successfully pulled 'smollm2:360m'")
            return True
        else:
            print(f"✗ Error pulling model: {result.stderr}")
            print("  You may need to pull it manually: ollama pull smollm2:360m")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Timeout while pulling model")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def setup_finetuned_model():
    """Setup the finetuned model from bundled GGUF file"""
    print("\n=== Setting up finetuned model: smollfinetuned ===")
    
    # Get the script directory
    script_dir = Path(__file__).parent
    models_dir = script_dir / 'models'
    modelfile_path = models_dir / 'Modelfile'
    gguf_file = models_dir / 'smollm2-360m-lora-finetuned-merged-f16.gguf'
    
    # Check if files exist
    if not modelfile_path.exists():
        print(f"✗ Modelfile not found at {modelfile_path}")
        return False
    
    if not gguf_file.exists():
        print(f"✗ GGUF file not found at {gguf_file}")
        print("  The finetuned model file is missing. Please ensure it's included in the deployment.")
        return False
    
    print(f"✓ Found GGUF file: {gguf_file.name} ({gguf_file.stat().st_size / (1024*1024):.1f} MB)")
    
    # Check if model already exists
    if check_model_exists('smollfinetuned'):
        print("✓ Model 'smollfinetuned' already exists")
        return True
    
    # Update Modelfile with absolute path to ensure it works
    # Read current Modelfile
    with open(modelfile_path, 'r') as f:
        modelfile_content = f.read()
    
    # Replace relative path with absolute path
    absolute_gguf_path = str(gguf_file.resolve())
    modelfile_content = modelfile_content.replace(
        'FROM smollm2-360m-lora-finetuned-merged-f16.gguf',
        f'FROM {absolute_gguf_path}'
    )
    
    # Write updated Modelfile temporarily
    temp_modelfile = models_dir / 'Modelfile.temp'
    with open(temp_modelfile, 'w') as f:
        f.write(modelfile_content)
    
    try:
        # Create model from Modelfile
        return create_model_from_modelfile('smollfinetuned', temp_modelfile)
    finally:
        # Clean up temp file
        if temp_modelfile.exists():
            temp_modelfile.unlink()

def main():
    """Main setup function"""
    print("=" * 60)
    print("Ollama Model Setup Script")
    print("=" * 60)
    
    # Check if Ollama is installed
    if not check_ollama_installed():
        print("\n✗ Ollama is not installed or not in PATH")
        print("\nPlease install Ollama from: https://ollama.ai")
        print("Then ensure 'ollama' is available in your PATH")
        sys.exit(1)
    
    print("✓ Ollama is installed")
    
    # Setup models
    base_success = setup_base_model()
    finetuned_success = setup_finetuned_model()
    
    # Summary
    print("\n" + "=" * 60)
    print("Setup Summary")
    print("=" * 60)
    print(f"Base model (smollm2:360m): {'✓ Ready' if base_success else '✗ Failed'}")
    print(f"Finetuned model (smollfinetuned): {'✓ Ready' if finetuned_success else '✗ Failed'}")
    
    if base_success and finetuned_success:
        print("\n✓ All models are ready!")
        print("\nYou can now start the application with: python app.py")
        return 0
    else:
        print("\n⚠ Some models failed to setup. Please check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
