FROM python:3.11-slim

WORKDIR /app

# Copy common library
COPY common/ /app/common/

# Copy retrieval app
COPY apps/retrieval/ /app/apps/retrieval/

# Install dependencies
RUN pip install --no-cache-dir -r /app/apps/retrieval/requirements.txt

# Expose port
EXPOSE 8001

# Start app
CMD ["uvicorn", "apps.retrieval.app:app", "--host", "0.0.0.0", "--port", "8001"]
