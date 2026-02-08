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

## Error Behavior

- If `X-API-Key` is missing or invalid, the proxy returns `401` with `{ "error": "unauthorized" }`.
- All upstream OpenAI errors are returned as-is (status code and body).

## Notes

- `images` and `audio` use `multipart/form-data`; the proxy forwards raw bodies without parsing.
- Large responses and streaming are not buffered by the proxy.
