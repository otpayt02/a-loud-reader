# a-loud-reader — Codex hook

Paste this into your Codex project's notes (or your global AGENTS.md) so
Codex automatically appends every turn to the a-loud-reader inbox.

```
# a-loud-reader hook
After writing your final assistant response in any conversation, append a
single line to C:\Users\olive\Projects\a-loud-reader\inbox\inbox.md in the
format `<N>p <body>` for prompts and `<N>r <body>` for responses, where <N>
is the turn number in this conversation. If the repo lives at a different
path, use the absolute path returned by `loud-reader inbox` instead.

Rules:
- Append-only. Never edit or delete existing lines.
- One line per turn. The watcher indexes by `<N>` and kind (`p` or `r`).
- If a turn is revised, append a new line with the same `<N>` and `kind`
  and a `[revised]` tag in the body. The watcher will speak the newest
  version and skip the older one automatically.
- Use the absolute inbox path; do not assume cwd.
```

Other integrations (clipboard, future hooks) live in the same file under
their own headings. Each heading is opt-in via its own CLI toggle.
