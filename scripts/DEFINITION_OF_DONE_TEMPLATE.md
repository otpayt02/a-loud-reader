# Definition of Done — <project-name>

> One sentence the user (or you) can read aloud. If this isn't true, the project
> isn't done. Pin it before writing any code.

**DoD:** _User runs `<command>`, observes `<observable>`._

## Why this exists

A Definition of Done (DoD) is the single sentence that, when true, lets you stop
working on a project. Every other checklist item is downstream of this. If you
can't write it in one sentence, the project isn't scoped tightly enough to start
coding.

## Template

Replace the placeholders below. Delete the rest after you fill it in.

```text
USER (who is the user?):
  <one phrase -- "me", "my team", "the public", "future me", ...>

RUNS (literal command, copy/paste-able):
  <"loud-reader status", "python app.py", "node scripts/run.js", ...>

OBSERVES (what they see / hear / feel, with their senses):
  <"hears a spoken MP3 in the background", "sees a tray icon",
   "reads a one-paragraph summary", ...>

IN <time-bound>:
  <"under 5 seconds", "within a single command", "first try", ...>

WITH THESE CONSTRAINTS:
  <"local-only", "offline", "no API key", "Python 3.12", ...>
```

## Worked example — a-loud-reader itself

```text
USER: me, on my Windows 11 laptop.
RUNS: loud-reader start; "1p hello" | Add-Content inbox\inbox.md
OBSERVES: hears "Prompt 1. hello." from the speakers within 5 seconds, with no
         media-player window popping up over their work.
IN: under 5 seconds, with the cursor in any PowerShell window.
WITH: PowerShell 5.1+, Python 3.12, an internet connection (Edge TTS).
```

## Anti-patterns — DoDs that aren't really DoDs

- "It works on my machine." (no observable)
- "It builds without errors." (no user, no observation)
- "I implemented all the features in the spec." (no finish line, no user)
- "Tests pass." (good but not sufficient alone -- still need user observation)

## When to update the DoD

- Before the project starts.
- Whenever the goal changes.
- Never after the work is done -- if it needs updating then, the project wasn't
  actually finished.

## How this fits into a-loud-reader's prompt-refinery meta-loop

Every canonical execution prompt from `loud-reader refine` ends with an
"ACCEPTANCE" line. That line is a one-sentence DoD. Treat it as binding: code
that doesn't move the project toward that sentence is out of scope.