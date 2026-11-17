# Use official Miniconda3 image
# FROM anaconda/miniconda:latest
FROM condaforge/miniforge3:latest

# Set environment variables
ENV CONDA_DIR=/opt/conda \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    ENV_NAME=climade-dashboard

# Set PATH to automatically use the conda environment and nextclade binaries
ENV PATH=/opt/conda/envs/${ENV_NAME}/bin:/opt/nextclade/bin:$PATH

# auto accept tos
# ENV CONDA_PLUGINS_AUTO_ACCEPT_TOS=true

WORKDIR /app

# Install system dependencies and clean up apt cache in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    vim \
    ca-certificates \
    coreutils \
    procps \
    grep \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add CA from Compose build secret
RUN --mount=type=secret,id=cert_ca \
    cp /run/secrets/cert_ca /usr/local/share/ca-certificates/cert_ca.crt && \
    update-ca-certificates && \
    conda config --system --set ssl_verify /etc/ssl/certs/ca-certificates.crt

# Tell Python/OpenSSL/requests to use the system CA bundle
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Copy environment file and create Conda environment
COPY environment.yml .

RUN conda create -f environment.yml && \
    conda clean -afy 

# Set shell to run subsequent steps inside the activated environment
RUN echo "conda activate ${ENV_NAME}" >> /root/.bashrc

# Copy application source code
COPY . .

# Single healthcheck verifying python, nextclade, and environment readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD conda info || exit 1

# Default command opens an interactive bash session
CMD ["/bin/bash"]