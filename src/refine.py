"""refine.py -- thin client for the local Prompt Refinery API.

When the user runs ``loud-reader refine "rough prompt"``, this script:

  1. POSTs the rough prompt to ``/api/turns`` as a USER turn so the Refinery's
     file writer appends it to the live conversation log.
  2. Calls ``/api/ai/generate`` (Gemini if ``GEMINI_API_KEY`` is set on the API
     server, otherwise the local deterministic engine) to get a refinement.
  3. Prints a structured refinement: refined understanding, clarification
     questions, canonical execution prompt, critique template, suggested next.

The output is designed to be pasted into Codex as a system prompt or to be the
input to a follow-up Codex turn.
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8787"


def _post(path, body):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(path):
    with urllib.request.urlopen(API + path, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def _refine_locally(rough: str, family: str = "circumstantial") -> dict:
    """Deterministic refinement when no AI provider is reachable.

    We always return a useful shape so the meta-loop never blocks the user on
    API availability. The structure mirrors the SPEC.md sections from the
    Refinery repo so downstream tooling can parse it.
    """
    rough = rough.strip()
    return {
        "provider": "local_deterministic",
        "refined_understanding": (
            "You asked to: " + rough + "\n\n"
            "Refinery couldn't reach an AI provider, so this is the deterministic pass. "
            "It captures the rough intent verbatim and asks the minimum set of "
            "high-leverage clarification questions."
        ),
        "clarification_questions": [
            {
                "id": "goal",
                "prompt": "What does success look like? (one sentence)",
                "options": [
                    "A working local MVP I can run from the command line",
                    "A polished portfolio piece I can deploy publicly",
                    "A reusable template for future similar projects",
                    "Just an answer / explanation, no code",
                ],
                "reason": "Finish line defines scope and effort.",
            },
            {
                "id": "stack",
                "prompt": "What stack / language / platform?",
                "options": ["Python (PowerShell glue)", "Node / TypeScript", "Pure PowerShell", "Something else"],
                "reason": "Affects which skills the assistant pulls in.",
            },
            {
                "id": "constraints",
                "prompt": "Hard constraints?",
                "options": [
                    "Must be local-only, no cloud",
                    "Must work offline",
                    "Must use a specific existing repo",
                    "No constraints",
                ],
                "reason": "Constrains the solution space.",
            },
        ],
        "canonical_execution_prompt": (
            "GOAL: " + rough + "\n\n"
            "DELIVERABLES: smallest working artifact that proves the goal is met.\n"
            "CONSTRAINTS: see clarification answers above.\n"
            "ACCEPTANCE: one-line Definition of Done, written before any code."
        ),
        "critique_template": (
            "1. Does the goal statement contain a finish line the user can observe?\n"
            "2. Are the deliverables the smallest set that proves the goal?\n"
            "3. Are constraints testable, not vibes?\n"
            "4. Will the Definition of Done block further work until it's true?\n"
            "5. Anything missing that the user is silently assuming?"
        ),
        "suggested_next_prompt": (
            "Before coding, write Definition of Done in one sentence: "
            "\"user runs <command>, sees/ hears <observable>.\""
        ),
    }


def _refine_with_provider(rough: str) -> dict:
    """Call /api/ai/generate and let the Refinery's Gemini path refine."""
    try:
        provider = _get("/api/provider")
    except Exception:
        return _refine_locally(rough)

    prompt = (
        "You are a deterministic prompt-refinement engine. Given ROUGH INPUT below, "
        "return a JSON object with EXACTLY these top-level keys and nothing else:\n"
        "  refined_understanding: 1-2 sentence summary of what is being asked.\n"
        "  clarification_questions: array of 2-4 objects with id (string), prompt (string), "
        "    options (array of 2-4 strings), reason (string).\n"
        "  canonical_execution_prompt: a single paste-ready block describing GOAL, "
        "    DELIVERABLES, CONSTRAINTS, ACCEPTANCE.\n"
        "  critique_template: 3-5 numbered questions to evaluate the canonical prompt.\n"
        "  suggested_next_prompt: one short prompt the user can paste next.\n"
        "Wrap the JSON in a ```json fenced block. Do not add any prose.\n\n"
        "ROUGH INPUT:\n" + rough
    )
    try:
        result = _post("/api/ai/generate", {"prompt": prompt})
    except Exception:
        return _refine_locally(rough)

    if not result.get("text"):
        return _refine_locally(rough)

    # Best-effort: try to parse the provider output as JSON. If it isn't JSON,
    # wrap it as the refined_understanding and synthesize the rest deterministically.
    text = result["text"].strip()
    # Strip markdown code fences that some providers wrap JSON in.
    # Pull the first ```json ... ``` block out of the response, regardless of
    # surrounding prose.
    # 1) Try a fenced ```json ... ``` block.
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    else:
        # 2) Try the largest {...} or [...] block in the response.
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last > first:
            text = text[first:last + 1]
    try:
        parsed = json.loads(text)
        parsed["provider"] = result.get("provider", "unknown")
        return parsed
    except Exception:
        base = _refine_locally(rough)
        base["refined_understanding"] = text
        base["provider"] = result.get("provider", "unknown")
        return base


def _append_user_turn(conversation_id: str, content: str) -> None:
    """Mirror the user's raw input into the Refinery's conversation log."""
    try:
        _post(
            "/api/turns",
            {
                "conversationId": conversation_id,
                "turn": {
                    "id": conversation_id + "." + str(int(time.time() * 1000) % 100000) + ".0",
                    "role": "user",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "state": "intake_received",
                    "content": content,
                },
            },
        )
    except Exception as e:
        print("[warn] could not append user turn to Refinery log:", e, file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(prog="refine.py")
    parser.add_argument("text", nargs="?", help="Rough prompt to refine. Use --file to read from disk.")
    parser.add_argument("--file", help="Read the rough prompt from this path.")
    parser.add_argument("--conversation-id", default="0001", help="Refinery conversation id (default: 0001).")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON instead of formatted text.")
    parser.add_argument("--canonical-only", action="store_true", help="Print only the canonical execution prompt.")
    args = parser.parse_args()

    if args.file:
        rough = Path(args.file).read_text(encoding="utf-8", errors="ignore")
    elif args.text:
        rough = args.text
    else:
        rough = sys.stdin.read()

    rough = rough.strip()
    if not rough:
        print("error: empty prompt", file=sys.stderr)
        return 2

    # Mirror the raw input into the Refinery's conversation log so it persists
    # alongside the refinement (audit trail).
    _append_user_turn(args.conversation_id, rough)

    # Run the refinement.
    refinement = _refine_with_provider(rough)

    if args.json:
        print(json.dumps(refinement, indent=2, ensure_ascii=False))
        return 0

    if args.canonical_only:
        print(refinement.get("canonical_execution_prompt", "").strip())
        return 0

    # Formatted, human-readable output. Mirrors the SPEC.md sections.
    out = []
    out.append("# Refined prompt (provider: " + str(refinement.get("provider", "?")) + ")")
    out.append("")
    out.append("## 1. Refined understanding")
    out.append(refinement.get("refined_understanding", "").strip())
    out.append("")
    out.append("## 2. Clarification questions")
    for q in refinement.get("clarification_questions", []) or []:
        out.append("- **" + str(q.get("id", "?")) + ":** " + str(q.get("prompt", "")))
        for opt in q.get("options", []) or []:
            out.append("  - " + str(opt))
        if q.get("reason"):
            out.append("  - _Reason:_ " + str(q["reason"]))
    out.append("")
    out.append("## 3. Canonical execution prompt")
    out.append("```")
    out.append(refinement.get("canonical_execution_prompt", "").strip())
    out.append("```")
    out.append("")
    out.append("## 4. Critique template")
    out.append(refinement.get("critique_template", "").strip())
    out.append("")
    out.append("## 5. Suggested next prompt")
    out.append(refinement.get("suggested_next_prompt", "").strip())
    out.append("")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())