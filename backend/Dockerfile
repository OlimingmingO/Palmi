# Stage 1: Builder (Python deps)
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    -r requirements.txt

# Stage 2: Runtime (Python + Node.js + PKE)
FROM python:3.11-slim

WORKDIR /app

# Install Node.js + npm for PKE engine
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Install qmd globally (PKE semantic search dependency)
RUN npm install -g --registry=https://registry.npmmirror.com qmd

# Copy and install PKE engine
COPY pke_engine/ /opt/pke/
RUN cd /opt/pke && npm install --registry=https://registry.npmmirror.com

# Make pke binary executable and add to PATH
RUN chmod +x /opt/pke/bin/pke || true
ENV PATH="/opt/pke/bin:$PATH"

# Copy Python deps from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
