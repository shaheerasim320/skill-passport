# Data Shapes

## Finding

```json
{
  "category": "network | filesystem | secrets | shell",
  "source": {
    "file": "sync.py",
    "line": 5,
    "description": "os.environ.get(\"OPENAI_API_KEY\")"
  },
  "sink": {
    "file": "sync.py",
    "line": 8,
    "description": "requests.post(...)"
  },
  "assignment_chain": [
    "api_key",
    "payload[\"key\"]",
    "requests.post(...)"
  ],
  "external_domain": "telemetry.auto-formatter.dev"
}
```

## Behavior Profile

```json
{
  "network": {
    "detected": true,
    "evidence": [],
    "external_domains": []
  },
  "filesystem": {
    "detected": true,
    "evidence": []
  },
  "secrets": {
    "detected": true,
    "evidence": []
  },
  "shell": {
    "detected": false,
    "evidence": []
  }
}
```

## Verdict

```json
{
  "trust_level": "verified | review | high_risk",
  "behavior_profile": {},
  "evidence": [],
  "classifications": [],
  "reasoning": {
    "judgment": "",
    "translation": ""
  },
  "recommendation": "",
  "install_command": ""
}
```

## `schemas/verdict.json` output-schema definition

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["trust_level", "behavior_profile", "evidence", "recommendation"],
  "properties": {
    "trust_level": {
      "type": "string",
      "enum": ["verified", "review", "high_risk"]
    },
    "behavior_profile": { "type": "object" },
    "evidence": { "type": "array" },
    "classifications": { "type": "array" },
    "reasoning": {
      "type": "object",
      "properties": {
        "judgment": { "type": "string" },
        "translation": { "type": "string" }
      }
    },
    "recommendation": { "type": "string" },
    "install_command": { "type": "string" }
  }
}
```

## SSE event

```json
{
  "event": "stage | profile | finding | verdict | error",
  "stage": "fetching | parsing | tracing | profiling | classifying | reasoning",
  "status": "",
  "finding": {},
  "behavior_profile": {},
  "verdict": {},
  "error": ""
}
```

