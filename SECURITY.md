# Security

## Source publication is not service deployment

This repository may be published as source code. The FastAPI and Next.js processes are local workstation tools by default, not internet services.

- Keep backend and frontend bound to loopback for normal use.
- Local API requests require both a loopback socket peer and a local Host value, plus one of the documented local frontend origins when an Origin header is present. A remote client cannot gain local privileges by sending `Host: localhost`.
- Non-local API Host access fails closed unless the operator sets `VOICE_LAB_API_TOKEN` and the caller sends it as a Bearer token.
- Never place that token in `NEXT_PUBLIC_*`, browser bundles, committed files, or client-side code. A remote deployment needs a server-side proxy/auth layer.
- `/media/*` remains local-only even when an API token is configured.
- Web-selected existing reference paths are limited to `refs/` and `voice_db/`. The explicit CLI remains the appropriate trusted local path boundary.

Do not expose the development processes directly to the internet. Use a reviewed authenticated reverse proxy if a service deployment is intentionally designed later.
