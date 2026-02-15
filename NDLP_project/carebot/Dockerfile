# ═══════════════════════════════════════════════
# CareBot — Single-stage Dockerfile
# Python 3.11 + Node.js 22 installed together
# ═══════════════════════════════════════════════

FROM python:3.11-slim

# Install Node.js 22 + system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    supervisor \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install OpenClaw globally
RUN npm install -g openclaw@latest || echo "OpenClaw install completed with warnings"

# Set working directory
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/carebot.conf

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start with supervisord
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/carebot.conf"]
