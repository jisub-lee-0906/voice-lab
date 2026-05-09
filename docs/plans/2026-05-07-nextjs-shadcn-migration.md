# Next.js shadcn Voice Lab Migration Plan

> **Status:** Completed and superseded by the current production layout. The Gradio prototype and top-level `app.py` shim are no longer kept; backend/frontend/CLI are the maintained surfaces.

> **For Hermes:** Historical plan only. Do not reintroduce legacy Gradio files from this document.

**Goal:** Replace the Gradio UI with a product-quality local web app using Next.js, shadcn/ui, TailwindCSS, Motion, and a FastAPI backend while preserving the existing GPT-SoVITS Python workflow.

**Architecture:** Keep Python responsible for ffmpeg/GPT-SoVITS/file-system work. `backend/` is the FastAPI API layer over `src/voice_lab`; `frontend/` is the Next.js App Router UI. Legacy Gradio files have been removed.

**Tech Stack:** Next.js 16, React 19, TypeScript, TailwindCSS 4, shadcn/ui, Motion for React, lucide-react, FastAPI, uvicorn, existing GPT-SoVITS + ffmpeg.

---

## Official docs checked

- Next.js installation docs: `https://nextjs.org/docs/app/getting-started/installation`
- shadcn/ui Next.js docs: `https://ui.shadcn.com/docs/installation/next`
- TailwindCSS Next.js framework guide: `https://tailwindcss.com/docs/installation/framework-guides/nextjs`
- Motion React quick start: `https://motion.dev/docs/react-quick-start`
- FastAPI first steps: `https://fastapi.tiangolo.com/tutorial/first-steps/`

Observed current package versions from npm:

- `next`: 16.2.5
- `react`: 19.2.6
- `tailwindcss`: 4.2.4
- `motion`: 12.38.0
- `lucide-react`: 1.14.0

## Tasks

### Task 1: Remove legacy Gradio surface

- Remove the old Gradio entrypoint and top-level `app.py` shim.
- Keep backend/frontend/CLI as the supported public surfaces.
- Keep tests adjusted so legacy UI-specific tests do not block the maintained stack.

### Task 2: Add FastAPI backend

- Create `backend/main.py`.
- Add endpoints:
  - `GET /api/health`
  - `GET /api/config`
  - `POST /api/reference`
  - `POST /api/generate`
  - `POST /api/save`
  - static files under `/media` for generated audio playback.
- Reuse existing `voice_lab.audio`, `voice_lab.gptsovits`, `voice_lab.workflow`.
- Add backend tests using FastAPI `TestClient`.

### Task 3: Create Next.js frontend

- Create `frontend/` with Next.js App Router + TypeScript + TailwindCSS.
- Use latest npm packages.
- Add shadcn-compatible local UI primitives under `frontend/src/components/ui/`.
- Use Motion for subtle result-card entry animations.

### Task 4: Build product-style Korean UI

- One page flow:
  - left: input form, voice file, desired feeling, text
  - right: status, reference preview, generated voice result list
- Avoid Gradio-like cards; use clean Linear/Raycast style.
- Use Korean copy for normal users:
  - “원하는 느낌”
  - “새 음성 만들기”
  - “마음에 드는 음성 저장”
- Candidate results should be vertical list, not unequal horizontal cards.

### Task 5: Verify

- Python tests: `uv run --extra dev pytest -q`
- Backend import/health route test.
- Frontend lint/build: `npm run lint` and `npm run build` from `frontend/`.
- Start backend and frontend in background; verify:
  - `http://127.0.0.1:8100/api/health`
  - `http://127.0.0.1:3100`
- Commit changes.
