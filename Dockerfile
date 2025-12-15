# Use a slim Debian image as our base
# (we don't use a Python image because Python will be installed with uv)
FROM debian:trixie-slim

# Set the working directory inside the container
WORKDIR /app

# Arguments needed at build-time, to be provided by Coolify
ARG DEBUG
ARG SECRET_KEY
ARG DATABASE_URL
ARG DJANGO_SETTINGS_MODULE

# Install system dependencies needed by our app
RUN apt-get update && apt-get install -y \
    build-essential \
    curl wget \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv, the fast Python package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy only the dependency definitions first to leverage Docker's layer caching
COPY pyproject.toml uv.lock .python-version ./

# Install Python dependencies for production (without dev dependencies)
RUN uv sync --no-dev

# Install Playwright browsers (Chromium for map thumbnails)
RUN uv run playwright install chromium --with-deps

# Copy the rest of the application code into the container
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Collect the static files
RUN uv run --no-sync ./manage.py collectstatic --noinput

# Migrate the database
RUN uv run --no-sync ./manage.py migrate

# Expose the port Gunicorn will run on
EXPOSE 8000

# Run entrypoint script (starts dbworker + gunicorn)
CMD ["./entrypoint.sh"]
