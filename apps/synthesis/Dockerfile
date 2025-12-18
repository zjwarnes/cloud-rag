FROM python:3.11-slim

WORKDIR /app

# Copy common library
COPY common/ /app/common/

# Copy synthesis app
COPY apps/synthesis/ /app/apps/synthesis/

# Install dependencies
RUN pip install --no-cache-dir -r /app/apps/synthesis/requirements.txt

# Expose port
EXPOSE 8002

# Start app
CMD ["uvicorn", "apps.synthesis.app:app", "--host", "0.0.0.0", "--port", "8002"]
