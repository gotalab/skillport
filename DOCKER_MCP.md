# Docker: SkillPort MCP Server (HTTP)

This repo ships the MCP server as the `skillport-mcp` command.

The goal of this Docker setup is to run `skillport-mcp` in **Remote mode (HTTP)**:

```bash
SKILLPORT_SKILLS_DIR=.skills uv run skillport-mcp --http --port=3000 --host=0.0.0.0
```

Inside Docker, `SKILLPORT_SKILLS_DIR` should come from env, and typically points to a mounted volume.

---

## Files

- `Dockerfile.mcp`: Multi-stage build using `uv`.
- `scripts/build-mcp-docker.sh`: Convenience builder.

---

## Build

```bash
./scripts/build-mcp-docker.sh
# or: ./scripts/build-mcp-docker.sh v1
```

Manual build:

```bash
docker build -f Dockerfile.mcp -t skillport-mcp:latest .
```

---

## Run (HTTP / Remote mode)

### Default (0.0.0.0:3000)

```bash
docker run -p 3000:3000 \
  -e SKILLPORT_SKILLS_DIR=/skills \
  -v "$(pwd)/.skills:/skills" \
  skillport-mcp:latest
```

The MCP endpoint will be:

- `http://localhost:3000/mcp`

### Custom host/port

```bash
docker run -p 8000:8000 \
  -e SKILLPORT_SKILLS_DIR=/skills \
  -v "$(pwd)/.skills:/skills" \
  skillport-mcp:latest \
  skillport-mcp --http --host 0.0.0.0 --port 8000
```

---

## Run (STDIO / Local mode)

If you want stdio transport (useful for local MCP client integration), run without `--http`:

```bash
docker run -i \
  -e SKILLPORT_SKILLS_DIR=/skills \
  -v "$(pwd)/.skills:/skills" \
  skillport-mcp:latest \
  skillport-mcp
```

---

## Notes / Tips

- If you want persistence for the index DB, mount the SkillPort home directory (defaults to `~/.skillport` inside the container user home). For example:

  ```bash
  docker run -p 3000:3000 \
    -e SKILLPORT_SKILLS_DIR=/skills \
    -v "$(pwd)/.skills:/skills" \
    -v "skillport-data:/home/app/.skillport" \
    skillport-mcp:latest
  ```

- Embeddings default to `SKILLPORT_EMBEDDING_PROVIDER=none`. If you set it to `openai`, you must also pass `OPENAI_API_KEY`.
