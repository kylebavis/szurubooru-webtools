#!/bin/bash

# Szuru Webtools - Quick Setup Script

echo "🚀 Setting up Szuru Webtools..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your Szurubooru credentials."
    echo ""
    echo "Required settings:"
    echo "  - SZURU_BASE: Your Szurubooru instance URL"
    echo "  - SZURU_USER: Your username"
    echo "  - SZURU_TOKEN: Your API token"
    echo ""
    echo "Edit .env file now? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
else
    echo "✅ .env file already exists"
fi

# Check if gallery-dl.conf exists
if [ ! -f gallery-dl.conf ]; then
    echo "⚠️  gallery-dl.conf not found. This file is required for the application to work properly."
    echo "A sample configuration is included in the repository."
else
    echo "✅ gallery-dl.conf found"
fi

echo ""
echo "🐳 Starting Docker Compose..."
docker-compose up -d

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Verify your .env settings are correct"
echo "  2. Customize gallery-dl.conf for your preferred sites"
echo "  3. Visit http://localhost:8000 to use the application"
echo ""
echo "📖 For more configuration options, see DEPLOYMENT.md"
echo ""
echo "🔍 Check status with: docker-compose ps"
echo "📜 View logs with: docker-compose logs -f"
