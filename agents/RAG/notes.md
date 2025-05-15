# Notes

## Initial setup - RAG

* fork source repo: https://github.com/google/adk-samples
* cd to directory
* install dependencies with poetry
* `cp /Users/justinjm/projects/github.com/justinjm/adk-
samples/agents/RAG/.env\ example /Users/justinjm/projects/github.com/justinjm/adk-samples/agents/RAG/.env`
* copy .env example file to env 
* create GCS staging bucket 

```sh
gsutil mb -c regional -l us-central1 gs://demos-vertex-ai-adk-samples-rag
```

```sh
poetry env activate 
```

```sh
source /Users/justinjm/Library/Caches/pypoetry/virtualenvs/rag-7XztYdRW-py3.13/bin/activate
```

