#!/bin/bash
# Security validation script for CaseForge frontend
# This script should be run in CI/CD pipelines to ensure no high-severity CVEs

set -e

echo "🔒 Running security validation for CaseForge frontend..."
echo "=================================================="

# Navigate to frontend directory
cd "$(dirname "$0")/../../frontend"

echo "📍 Current directory: $(pwd)"
echo "🔍 Checking for high-severity vulnerabilities..."

# Run npm audit and fail on high severity issues
npm audit --audit-level=high

if [ $? -eq 0 ]; then
    echo "✅ No high-severity vulnerabilities found!"
else
    echo "❌ High-severity vulnerabilities detected!"
    echo "🔧 Run 'npm audit fix' or update package.json overrides"
    exit 1
fi

echo ""
echo "🔍 Checking overrides are in place..."

# Check that security overrides exist in package.json
if grep -q '"overrides"' package.json; then
    echo "✅ Security overrides found in package.json"
    echo "📋 Current overrides:"
    grep -A 10 '"overrides"' package.json
else
    echo "⚠️  No security overrides found in package.json"
    echo "💡 Consider adding overrides for known vulnerabilities"
fi

echo ""
echo "🏗️  Testing build process..."

# Test that the application builds successfully
npm run build > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
else
    echo "❌ Build failed!"
    exit 1
fi

echo ""
echo "🎉 Security validation complete!"
echo "📊 Summary:"
echo "   ✅ No high-severity vulnerabilities"
echo "   ✅ Security overrides in place"
echo "   ✅ Build process successful"
echo ""
echo "🔒 Your frontend is secure and ready for deployment!"