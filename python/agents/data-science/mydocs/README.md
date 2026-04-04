# Setup Guide

Deploy a data science agent with BigQuery data to Vertex AI Agent Engine and register it in the Gemini Enterprise agent catalog.

## Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI configured
- `uv` package manager installed
- Required GCP APIs enabled:
  - Vertex AI API
  - Agent Builder API
  - BigQuery API

## Quick Start

```bash
# Clone and navigate to project
git clone https://github.com/justinjm/adk-samples.git
cd python/agents/data-science

# Set up environment
uv sync
source .venv/bin/activate

# Configure environment variables
cp .env.example .env 
# cp toolbox.env-example .toolbox.env # TODO - confirm?
# Edit .env with your values
cp registration/.env-registration-example registration/.env-registration

# Test locally
uv run adk web

# Deploy
uv build --wheel --out-dir deployment
cd deployment && python3 deploy.py --create
```

## Detailed Setup

### 1. Get Code

```bash
git clone https://github.com/justinjm/adk-samples.git
cd adk-samples/python/agents/data-science
```

### 2. Set Up Environment

```bash
# Sync dependencies
uv sync
source .venv/bin/activate

# Configure environment
cp toolbox.env-example .env
# Edit .env with your project-specific values
```

### 3. Test Agent Locally

```bash
uv run adk web
```

## Deployment

### Setup BigQuery data 

Run script to create a synthetic dataset and then upload it to BigQuery:

```bash
python3 myutils/generate_upload_data.py
```  

### Build Agent Package

From the `data-science` directory:

```bash
uv build --wheel --out-dir deployment
```

This creates `data_science-0.1.0-py3-none-any.whl` in the `deployment` directory.

### Deploy to Agent Engine

```bash
cd deployment/
python3 deploy.py --create
```

**Expected output:**

```
Creating Extension
Create Extension backing LRO: projects/.../locations/us-central1/extensions/.../operations/...
Extension created. Resource name: projects/.../locations/us-central1/extensions/...
Successfully created agent: projects/.../locations/us-central1/reasoningEngines/XXXXXXX
```

**Save the Resource ID** from the final line (the numerical value after `reasoningEngines/`).

### Test Deployment

```bash
# Set environment variables
export PROJECT_ID=$(gcloud config get-value project)
export GOOGLE_CLOUD_STORAGE_BUCKET="${PROJECT_ID}-adk-staging"
export RESOURCE_ID=<your_resource_id>
export USER_ID="user1"

# Run test
uv run python3 test_deployment.py --resource_id=$RESOURCE_ID --user_id=$USER_ID
```

## Registration in Gemini Enterprise

### Configure Registration

```bash
cd ../registration/

# Copy and edit registration environment file
cp .env-registration-example .env-registration
# Edit .env-registration with your values

# Load environment variables
source .env-registration
```

### Set Required Variables

```bash
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export LOCATION="us-central1"
export ADK_DEPLOYMENT_ID=<your_resource_id>
```

### Register Agent

```bash
curl -X POST \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: ${PROJECT_ID}" \
"https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/${APP_ID}/assistants/default_assistant/agents" \
-d "{
    \"displayName\": \"${DISPLAY_NAME}\",
    \"description\": \"${DESCRIPTION}\",
    \"adk_agent_definition\": {
        \"tool_settings\": {
            \"tool_description\": \"${TOOL_DESCRIPTION}\"
        },
        \"provisioned_reasoning_engine\": {
            \"reasoning_engine\": \"projects/${PROJECT_ID}/locations/${LOCATION}/reasoningEngines/${ADK_DEPLOYMENT_ID}\"
        }
    }
}"
```

The agent should now be available in Gemini Enterprise.

## Verification

### View Registered Agent

```bash
export AGENT_RESOURCE_ID=<agent_id_from_registration_response>
export AGENT_RESOURCE_NAME="projects/${PROJECT_NUMBER}/locations/global/collections/default_collection/engines/${APP_ID}/assistants/default_assistant/agents/${AGENT_RESOURCE_ID}"

curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/${AGENT_RESOURCE_NAME}"
```

### List All Registered Agents

```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/${APP_ID}/assistants/default_assistant/agents"
```

## Cleanup

### Delete Agent from Gemini Enterprise

Update `AGENT_RESOURCE_ID` with the value from the registration response or list command:

```bash
curl -X DELETE \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/${AGENT_RESOURCE_NAME}"
```

### Delete Deployed Agent from Agent Engine

```bash
# WARNING: This will delete the deployed agent
uv run python deployment/deploy.py --delete --resource_id=$RESOURCE_ID
```

### Delete Vertex AI Extensions

Delete all extensions:
```bash
uv run python delete_extensions.py --mode delete_all --project_id $PROJECT_ID
```

Delete specific extensions:
```bash
uv run python delete_extensions.py --mode delete_list --ids 1111111111111111 222222222222222 --project_id $PROJECT_ID
```

### Delete BigQuery Resources

[Documentation](https://cloud.google.com/bigquery/docs/managing-datasets#delete-datasets)

```bash
# Uncomment to delete
# bq rm -r -f -d ${PROJECT_ID}:forecasting_sticker_sales
```

### Delete GCS Staging Bucket

[Documentation](https://cloud.google.com/storage/docs/deleting-buckets)

```bash
# Uncomment to delete
# gcloud storage rm --recursive gs://${PROJECT_ID}-adk-staging
```

## References

- [VeerMuchandi/corporate_analyst](https://github.com/VeerMuchandi/corporate_analyst) - Example corporate analyst agent