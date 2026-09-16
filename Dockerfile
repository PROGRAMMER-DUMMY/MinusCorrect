# MinusCorrect Hardened Container Environment
# Provides execution isolation, non-root privileges, and pinned dependencies for autonomous supervision.

FROM python:3.13-slim

# Prevent interactive prompts and Python byte-code pollution
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (git, ca-certificates)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged runtime user
RUN groupadd -g 10001 minuscorrect && \
    useradd -u 10001 -g minuscorrect -m -d /home/minuscorrect -s /bin/bash minuscorrect

# Configure Git safe directory for non-root user
RUN git config --system --add safe.directory "*"

WORKDIR /app

# Copy project manifest and install dependencies
COPY pyproject.toml README.md ./
COPY minuscorrect/ minuscorrect/
RUN pip install --no-cache-dir pytest .

# Set up runtime workspace directory with permissions
WORKDIR /workspace
RUN chown -R minuscorrect:minuscorrect /workspace /app /home/minuscorrect

USER minuscorrect

ENTRYPOINT ["minuscorrect"]
CMD ["--help"]
