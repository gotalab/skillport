#!/usr/bin/env bash
# Build script for SkillPort MCP Server Docker image

set -euo pipefail

IMAGE_NAME="skillport-mcp"
TAG="${1:-latest}"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

echo "🐳 Building Docker image: ${FULL_IMAGE_NAME}"

docker build -f Dockerfile.mcp -t "${FULL_IMAGE_NAME}" .

echo "✅ Built: ${FULL_IMAGE_NAME}"

# Show image info
echo ""
echo "📊 Image information:"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedSince}}"

cat <<EOF

🚀 Run (HTTP mode, default):
  docker run -p 3000:3000 \
    -e SKILLPORT_SKILLS_DIR=/skills \
    -v "$(pwd)/.skills:/skills" \
    ${FULL_IMAGE_NAME}

🔍 Run (HTTP mode, custom host/port):
  docker run -p 8000:8000 \
    -e SKILLPORT_SKILLS_DIR=/skills \
    -v "$(pwd)/.skills:/skills" \
    ${FULL_IMAGE_NAME} skillport-mcp --http --host 0.0.0.0 --port 8000

🛠️ Run (STDIO mode):
  docker run -i \
    -e SKILLPORT_SKILLS_DIR=/skills \
    -v "$(pwd)/.skills:/skills" \
    ${FULL_IMAGE_NAME} skillport-mcp
EOF
