FROM python:3.11-slim

WORKDIR /app

# Copy common library
COPY common/ /app/common/

# Copy ingestion app
COPY apps/ingestion/ /app/apps/ingestion/

# Install dependencies
RUN pip install --no-cache-dir -r /app/apps/ingestion/requirements.txt

# Expose port
EXPOSE 8000

# Start app
CMD ["uvicorn", "apps.ingestion.app:app", "--host", "0.0.0.0", "--port", "8000"]
