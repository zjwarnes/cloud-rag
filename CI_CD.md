# CI/CD Pipeline Documentation

## Overview

This project uses GitHub Actions to automate testing and Docker image building. The pipeline enforces isolation by running tests twice:
1. **Direct pytest execution** - Tests run directly in the CI environment
2. **Docker-based tests** - Tests run inside the containerized environment

This ensures the application works both locally and in production containers.

## Workflow: `.github/workflows/ci.yml`

### Triggers
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

### Jobs

#### 1. **test-and-build** (Matrix Strategy)
Runs in parallel for each service: `ingestion`, `retrieval`, `synthesis`, `frontend`

For each service:
1. **Install Dependencies** - Installs Python packages from `requirements.txt`
2. **Run Direct Tests** - Executes `pytest` in the local environment
3. **Build Docker Image** - Builds the Dockerfile using Docker Buildx with layer caching
4. **Run Docker Tests** - Executes tests inside the container to verify they pass in production

**Isolation Benefits:**
- Direct tests catch environment-specific issues early
- Docker tests verify containerization works correctly
- Both must pass before code is considered valid

#### 2. **lint-and-type-check**
Runs style and type checking:
- **flake8** - Python syntax and style validation
- Runs independently, doesn't block build (continues on error)

#### 3. **summary**
Final check that depends on both previous jobs. Fails if either job failed.

## Local Testing

Before pushing, you can test locally:

```bash
# Test a single service locally
cd apps/ingestion
python -m pip install -r requirements.txt
pytest tests/ -v

# Build and test the Docker image
docker build -t rag-ingestion:latest -f Dockerfile ..
docker run --rm rag-ingestion:latest python -m pytest apps/ingestion/tests/ -v
```

## Running All Services

```bash
# Test all services in parallel (simulating CI)
for service in ingestion retrieval synthesis frontend; do
  echo "Testing $service..."
  cd /home/zac/gcp-rag/apps/$service
  pytest tests/ -v || exit 1
  docker build -t rag-$service:latest -f Dockerfile ../..
  docker run --rm rag-$service:latest python -m pytest apps/$service/tests/ -v || exit 1
done
```

## Deployment

Only images built from passing CI/CD runs should be deployed:

```bash
# Push images (typically done automatically after CI passes)
docker tag rag-ingestion:latest gcr.io/PROJECT_ID/rag-ingestion:latest
docker push gcr.io/PROJECT_ID/rag-ingestion:latest
```

## GitHub Actions Secrets (if needed)

For GCP deployment, add secrets in GitHub:
- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_SA_KEY` - Service account JSON key (base64 encoded)

These can be used in a deployment job when ready.

## Troubleshooting

### Tests pass locally but fail in CI
- Check Python version (should be 3.11)
- Verify all dependencies in `requirements.txt`
- Check for hardcoded paths or system dependencies

### Docker tests fail but direct tests pass
- Check Dockerfile `COPY` commands have correct paths
- Verify working directory (`WORKDIR /app`)
- Ensure all required files are included in build context

### Build cache not being used
- GitHub Actions caches layer by default with `cache-from: type=gha`
- Clear cache in Actions settings if needed

## Next Steps

1. **Push this workflow** to your repository
2. **Create a pull request** to trigger the workflow
3. **Monitor the Actions tab** for results
4. **Add deployment job** once tests pass consistently
