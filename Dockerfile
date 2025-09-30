FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DOWNLOAD_DIR=/downloads

# Install system deps (ffmpeg for yt-dlp)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# Copy source
COPY src /app/src

# Create downloads dir
RUN mkdir -p ${DOWNLOAD_DIR}
VOLUME ["/downloads"]

CMD ["python", "-m", "src.bot"]
