# Setup notes

Deployment of data science agent for data in BigQuery.

Deployed to agent engine and registered in gemini enterprise agent catalog.

## get code 

```sh
git clone https://github.com/justinjm/adk-samples.git
cd adk-samples/python/agents/data-science
# cd /python/agents/data-science # or if repo already downloaded
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
Successfully created agent: projects/647233624236/locations/us-central1/reasoningEngines/1470345013987639296
```


## TODO 

* [ ] create env-registration
* [ ] register new agent to gemini enterprise