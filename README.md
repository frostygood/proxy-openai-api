# OpenAI Proxy (FastAPI)

Minimal FastAPI proxy for OpenAI with a fixed `X-API-Key` and a single server-side OpenAI key. The proxy is transparent: it forwards parameters like `temperature`, `top_p`, `top_k`, `max_tokens`, `presence_penalty`, etc. without modification.

## What It Does

- Accepts client requests on `/v1/...`.
- Validates `X-API-Key` (fixed value stored in env).
- Replaces `Authorization` with the server-side `OPENAI_API_KEY`.
- Passes through request body, headers, query params, and streaming output.

## Supported Endpoints

- `/v1/responses`
- `/v1/chat/completions`
- `/v1/completions`
- `/v1/embeddings`
- `/v1/images/*`
- `/v1/audio/*`

No websocket/realtime support.

## Configuration

Create `.env` from `.env.example` and fill in values:

```
OPENAI_API_KEY=sk-your-openai-key
PROXY_X_API_KEY=change-me
OPENAI_BASE_URL=https://api.openai.com
```

- `OPENAI_API_KEY` is the master key used for all upstream requests.
- `PROXY_X_API_KEY` is the fixed key clients must send in `X-API-Key`.
- `OPENAI_BASE_URL` is optional (default: `https://api.openai.com`).

## Run With Docker Compose

```bash
docker compose up -d --build
```

The service listens on `18443`.

## Usage

All requests go to `http://<host>:18443/v1/...` and must include `X-API-Key`.

### Responses

```bash
curl http://localhost:18443/v1/responses \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"model":"gpt-4.1-mini","input":"Hello"}'
```

#### Responses (Streaming)

```bash
curl -N http://localhost:18443/v1/responses \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"model":"gpt-4.1-mini","input":"Say pong","stream":true}'
```

### Chat Completions

```bash
curl http://localhost:18443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Hi"}],"temperature":0.7}'
```

#### Chat Completions (Streaming)

```bash
curl -N http://localhost:18443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Say pong"}],"stream":true}'
```

### Completions

```bash
curl http://localhost:18443/v1/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"model":"gpt-3.5-turbo-instruct","prompt":"Say hello","max_tokens":16}'
```

### Embeddings

```bash
curl http://localhost:18443/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"model":"text-embedding-3-small","input":"Hello"}'
```

### Images

```bash
curl http://localhost:18443/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"model":"gpt-image-1","prompt":"Minimal logo","size":"1024x1024"}'
```

### Images (Edits)

```bash
curl http://localhost:18443/v1/images/edits \
  -H "X-API-Key: change-me" \
  -F image=@input.png \
  -F prompt="Add a blue background" \
  -F model=gpt-image-1
```

### Audio (Transcriptions)

```bash
curl http://localhost:18443/v1/audio/transcriptions \
  -H "X-API-Key: change-me" \
  -F file=@speech.mp3 \
  -F model=whisper-1
```

### Audio (Translations)

```bash
curl http://localhost:18443/v1/audio/translations \
  -H "X-API-Key: change-me" \
  -F file=@speech.mp3 \
  -F model=whisper-1
```

### Audio (Speech)

```bash
curl http://localhost:18443/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"model":"gpt-4o-mini-tts","voice":"alloy","format":"mp3","input":"Hello"}' \
  --output speech.mp3
```

## SDK Examples

### Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:18443/v1",
    api_key="unused",
    default_headers={"X-API-Key": "change-me"},
)

resp = client.responses.create(
    model="gpt-4.1-mini",
    input="Hello",
)

print(resp.output_text)
```

### Node.js

```js
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://localhost:18443/v1",
  apiKey: "unused",
  defaultHeaders: { "X-API-Key": "change-me" },
});

const resp = await client.responses.create({
  model: "gpt-4.1-mini",
  input: "Hello",
});

console.log(resp.output_text);
```

## Error Behavior

- If `X-API-Key` is missing or invalid, the proxy returns `401` with `{ "error": "unauthorized" }`.
- All upstream OpenAI errors are returned as-is (status code and body).

## Troubleshooting

- `401 unauthorized`: missing or wrong `X-API-Key`.
- `404 Not found`: endpoint not in the supported list or missing `/v1` in the URL.
- `Invalid file format`: audio must be `flac/m4a/mp3/mp4/mpeg/mpga/oga/ogg/wav/webm`.
- Image errors: `gpt-image-1` supports sizes `1024x1024`, `1024x1536`, `1536x1024`, or `auto`.
- Streaming seems stuck: ensure your client uses `stream: true` and does not buffer SSE.

## Notes

- `images` and `audio` use `multipart/form-data`; the proxy forwards raw bodies without parsing.
- Large responses and streaming are not buffered by the proxy.
