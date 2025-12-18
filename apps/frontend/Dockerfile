FROM python:3.11-slim

WORKDIR /app

# Copy common library
COPY common/ /app/common/

# Copy frontend app
COPY apps/frontend/ /app/apps/frontend/

# Install dependencies
RUN pip install --no-cache-dir -r /app/apps/frontend/requirements.txt

# Expose port
EXPOSE 8003

# Start app
CMD ["uvicorn", "apps.frontend.app:app", "--host", "0.0.0.0", "--port", "8003"]
