#!/bin/bash
# MFDE Pre-Submission Validation Script

echo "🔍 Starting OpenEnv Compliance Check..."

# 1. Check Files
echo "📁 Checking required files..."
FILES=("env.py" "models.py" "tasks.py" "grader.py" "inference.py" "app.py" "openenv.yaml" "Dockerfile" "requirements.txt")
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  [OK] $file exists"
    else
        echo "  [FAIL] $file is missing!"
        exit 1
    fi
done

# 2. Check openenv.yaml
echo "📄 Validating openenv.yaml..."
if grep -q "name:" "openenv.yaml" && grep -q "tasks:" "openenv.yaml"; then
    echo "  [OK] openenv.yaml looks valid"
else
    echo "  [FAIL] openenv.yaml is malformed"
    exit 1
fi

# 3. Check Dockerfile
echo "🐳 Checking Dockerfile..."
if grep -q "useradd -m -u 1000" "Dockerfile"; then
    echo "  [OK] Dockerfile follows HF Spaces UID 1000 requirement"
else
    echo "  [WARNING] Dockerfile might not be optimized for HF Spaces UID 1000"
fi

# 4. Check Inference Script Syntax
echo "🤖 Checking inference.py syntax..."
python -m py_compile inference.py
if [ $? -eq 0 ]; then
    echo "  [OK] inference.py syntax is valid"
else
    echo "  [FAIL] inference.py has syntax errors"
    exit 1
fi

echo "✅ VALIDATION COMPLETE: Your project is ready for submission!"
echo "🚀 Next Step: Push to Hugging Face and verify the space logs."
