#!/bin/bash

# FiscalShield IDP Development Environment Setup
# This script configures your business development environment

echo "🚀 Setting up FiscalShield IDP development environment..."

# Set AWS Profile to business account
export AWS_PROFILE=josqa
echo "✓ AWS Profile set to: josqa"

# Verify AWS account
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✓ Connected to AWS Account: $AWS_ACCOUNT"
else
    echo "⚠ Warning: Could not verify AWS connection"
fi

# Activate the virtual environment
if [ -d "/home/josian/git/fiscalshield-idp-core/idp-linux" ]; then
    source /home/josian/git/fiscalshield-idp-core/idp-linux/bin/activate
    echo "✓ Python virtual environment activated"
else
    echo "⚠ Warning: Virtual environment not found at idp-linux/"
fi

# Verify Git remote
GIT_REMOTE=$(git remote get-url origin 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✓ Git remote: $GIT_REMOTE"
else
    echo "⚠ Warning: Could not get git remote"
fi

echo "✅ Environment ready for development!"
echo ""
echo "Current configuration:"
echo "  AWS Profile: $AWS_PROFILE"
echo "  AWS Account: $AWS_ACCOUNT"
echo "  Working Directory: $(pwd)"
echo ""
