# search skill

## Purpose
Web search via local SearXNG instance. {{AGENT_NAME}} calls this to research things she doesn't already know.

## Usage
```python
from skills.search import search
results = search("query", n=5)
```

## Config
`SEARXNG_URL` env var (default: `http://127.0.0.1:8080/search`)
