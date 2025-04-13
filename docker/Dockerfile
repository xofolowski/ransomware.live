# Use an official Python runtime as the base image
FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
#RUN apt-get update && apt-get install -y \
#    build-essential \
#    libssl-dev \
#    libffi-dev \
#    python3-dev \
#    && rm -rf /var/lib/apt/lists/*


# Create a directory for the app
WORKDIR /ransomware.live

# Copy everything
#COPY --exclude=.git --exclude=.github --exclude=.gitignore . .
COPY . .
RUN rm -rf docker .git .github .gitignore

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "ransomcmd.py", "--api", "8080"]