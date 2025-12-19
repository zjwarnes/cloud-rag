#!/bin/bash

# RAG Deployment Script
# This script deploys your 4-microservice RAG system to Google Cloud

set -e

echo "🚀 RAG Cloud Deployment Script"
echo "======================================"

# Check if API keys are set
if [ -z "$TF_VAR_openai_api_key" ] || [ -z "$TF_VAR_pinecone_api_key" ]; then
    echo "❌ Error: API keys not set!"
    echo ""
    echo "Set them with:"
    echo "  export TF_VAR_openai_api_key='sk-...'"
    echo "  export TF_VAR_pinecone_api_key='pcsk_...'"
    exit 1
fi

echo "✅ API keys configured"

# Navigate to terraform directory
cd terraform

echo ""
echo "📋 Running Terraform Plan..."
terraform plan -out=tfplan

echo ""
echo "⚠️  Review the plan above. Do you want to apply these changes?"
echo "Type 'yes' to continue or 'no' to cancel:"
read -r response

if [ "$response" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

echo ""
echo "🔨 Applying Terraform Configuration..."
terraform apply tfplan

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📝 Service URLs:"
terraform output -json | jq '.service_urls.value'

echo ""
echo "🧪 Test your services:"
terraform output -json | jq '.test_commands.value'
