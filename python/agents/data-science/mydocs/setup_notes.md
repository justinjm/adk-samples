# Setup notes

Deployment of data science agent for data in BigQuery.

Deployed to agent engine and registered in gemini enterprise agent catalog.

## get code 

```bash
git clone https://github.com/justinjm/adk-samples.git
cd adk-samples/python/agents/data-science
```

```bash
cd python/agents/data-science # or if repo already downloaded
```

#### get code - sparse checkout 

```sh
git clone https://github.com/justinjm/adk-samples.git
cd adk-samples/
git sparse-checkout set --cone
git sparse-checkout add python/agents/data-science
cd /python/agents/data-science
```

disable sparse checkout

```sh
git sparse-checkout disable
```

## copy .env.example to .env s

```sh
cp .env.example .env
```


## setup environment 

```sh
uv sync
source .venv/bin/activate
```



## update .env

Notes

```sh
# .env 
# ...
DATASET_CONFIG_FILE='./forecasting_sticker_sales_dataset_config.json' # used in previous agent version
# ...
```

## test agent locally

```sh
uv run adk web
```

## deploy agent


Next, you need to create a `.whl` file for your agent. From the `data-science`
directory, run this command:

```bash
uv build --wheel --out-dir deployment
```

This will create a file named `data_science-0.1.0-py3-none-any.whl` in the
`deployment` directory.

Then run the below command. This will create a staging bucket in your GCP
project and deploy the agent to Vertex AI Agent Engine:

```bash
cd deployment/
```

```bash
python3 deploy.py --create
```

```txt
Creating Extension
Create Extension backing LRO: projects/647233624236/locations/us-central1/extensions/1111111111111/operations/zzzzzzzzzzzzzzz
Extension created. Resource name: projects/647233624236/locations/us-central1/extensions/1111111111111


```

### deployment success

```bash
Successfully created agent: projects/647233624236/locations/us-central1/reasoningEngines/XXXXXXX
```

Copy / paste the final numerical value in the command below and then run it.

#### test deployment 

```sh
export GOOGLE_CLOUD_STORAGE_BUCKET="${PROJECT_ID}-adk-staging" # if error, uncomment and re-run commands
export RESOURCE_ID=3529573612405129216
export USER_ID="user1"
uv run python3 test_deployment.py --resource_id=$RESOURCE_ID --user_id=$USER_ID
```



### WIP ==============================================================================

## TODO 

* [ ] create env-registration
* [ ] IAM setup steps
  * [ ] give `service-PROJECT=NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com` storage admin 
* [ ] register new agent to gemini enterprise

```bash
cd ../registration/ && source .env-registration
```


#### Setup 

```sh
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
export LOCATION="us-central1"
export APP_ID="gemini-enterprise-17748970_1774897077936" # ID of agentspace app 
```


#### register agent with agentspace

Lastly, we register the agent with agentspace by running the below.

Note we set the `ADK_DEPLOYMENT_ID` here to be sure it's correct and so we do not have to check/reload the `.env-registration` file again

Note: double check the `location` parameter in the `reasoning_engine` field below matches your `.env` file 

```bash
export ADK_DEPLOYMENT_ID=$RESOURCE_ID

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
            \"reasoning_engine\": \"projects/${PROJECT_ID}/locations/us-central1/reasoningEngines/${ADK_DEPLOYMENT_ID}\"
        }
    }
}"
```

Now the agent should be ready to use in Agentspace.



#### View agent

```bash
export AGENT_RESOURCE_ID=9126253323957889649
export AGENT_RESOURCE_NAME="projects/${PROJECT_NUMBER}/locations/global/collections/default_collection/engines/${APP_ID}/assistants/default_assistant/agents/${AGENT_RESOURCE_ID}"
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/${AGENT_RESOURCE_NAME}"
```

### CLEANUP

#### View all agents registered in agentspace

```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/${APP_ID}/assistants/default_assistant/agents"
```

#### Delete agent from Agentspace

Update the `AGENT_RESOURCE_ID` with the value from running command above to list all agents OR from the response message (`name`) after registring the agent.

```bash
curl -X DELETE \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/${AGENT_RESOURCE_NAME}"
```

#### Delete deployed agent in Agent Engine

```sh
## WARNING! will delete deployed agent
#uv run python deployment/deploy.py --delete --resource_id=$RESOURCE_ID
```

#### Delete vertex ai extension(s) - included scripts delete all or selected

```sh
uv run python delete_extensions.py --mode delete_all --project_id $PROJECT_ID
uv run python delete_extensions.py --mode delete_list --ids 1111111111111111 222222222222222 --project_id $PROJECT_ID
```

#### Delete BQ dataset / table

https://cloud.google.com/bigquery/docs/managing-datasets#delete-datasets

```sh
# bq rm -r -f -d ${PROJECT_ID}:forecasting_sticker_sales
```

#### Delete GCS bucket

https://cloud.google.com/storage/docs/deleting-buckets

```sh

# gcloud storage rm --recursive gs://${PROJECT_ID}-adk-staging
```


## References

* [VeerMuchandi/corporate\_analyst](https://github.com/VeerMuchandi/corporate_analyst) - example corporate analyst agent