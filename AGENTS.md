# AGENTS.md — a-loud-reader prompt-refinery auto-loop

> Applies to every Codex session whose project includes `a-loud-reader` as a
> dependency or sub-tool. The intent is to make every rough user prompt pass
> through the local Prompt Refinery before Codex acts on it.

## What this file does

It tells Codex (the assistant) to run any rough prompt through the local
Prompt Refinery (`loud-reader refine "<text>"`) BEFORE answering, and to use
the **canonical execution prompt** returned by the refinery as the actual
instruction. The refinement itself is appended to the Refinery app's live
conversation log so every interaction is auditable.

## Steps Codex must follow on every user turn

1. Treat the user's input as a rough prompt.
2. Run `loud-reader refine "<rough prompt>"` to get a structured refinement.
3. If the refinery returned clarifying questions, prefer the canonical execution
   prompt as the working instruction.
4. Reply using the canonical execution prompt as the system prompt for the turn.
5. Save the canonical prompt back into the running Codex thread as the
   authoritative task definition.

## Required environment

- `loud-reader` is on `PATH` (run `bin/install_path.cmd` once per machine).
- The Refinery API is reachable at `http://127.0.0.1:8787`. Start it with:
  ```powershell
  cd C:\Users\olive\Projects\portfolio_hub\prompt-refinery
  node server\fileWriter.cjs
  ```
- `GEMINI_API_KEY` may be set on the Refinery API host to enable Gemini-backed
  refinement. Without it the refinery falls back to a deterministic pass.

## Failure modes Codex should handle

- **Refinery API down**: fall back to the local deterministic pass; never block
  the user on the API.
- **`loud-reader` not on PATH**: run the bundled `python src/refine.py` directly.
- **Refinery returns `clarification_questions`**: ask the user to pick one
  option from each before doing work. This is the acceptance handshake.

## Why this exists

The local Refinery is the source of truth for what a good prompt looks like in
this user's workflow. Routing every prompt through it produces a self-reinforcing
loop: every Codex turn gets refined, every refinement is logged, the Refinery's
prompt library grows with each conversation, and future projects inherit the
patterns.