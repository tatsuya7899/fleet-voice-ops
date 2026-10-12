# Project description — fleet-voice-ops

用途: 提出フォームの「プロジェクトの説明」欄の素案(英語・そのまま貼れる形)。

## Inspiration

I run several coding agents in parallel (Devin CLI sessions). The failure mode
I actually hit: I walk away to cook, come back, and one agent has been waiting
for my input for 30 minutes while another crashed silently. Checking a screen
defeats the point of stepping away — I wanted to *ask* what was happening and
get an answer that respects the fact that I cannot look at a display.

## What it does

fleet-voice-ops is an MCP server that turns parallel coding-agent sessions
into a voice-queryable fleet:

- **`fleet_status`** — per-session liveness (`active` / `stalled_suspect` /
  `dead`), derived from PID liveness checks and last-activity timestamps —
  never from conversation contents.
- **`whats_stuck`** — the voice-first question: "anything going on?" answered
  in one spoken sentence.
- **`analyze_stall`** — the agentic part: multiple ranked hypotheses
  (`waiting_on_human_input`, `blocked_by_unresolved_error`, …), each with
  confidence and the evidence signals behind it, plus one recommended action.
- **`request_resume`** — a write action guarded by human-in-the-loop voice
  approval: confirmation requires speaking the session name, never a number,
  so a misheard digit cannot fire the wrong action.

The demo asks from the kitchen, hears that one session waits for input and one
died, approves resuming the dead session — no screen involved.

## How we built it

Python MCP server over Streamable HTTP with a Bearer auth middleware, verified
end-to-end through an ngrok tunnel from a generic MCP client. Session state is
read from `devin list --format json`, PID lock files
(`os.kill(pid, 0)` liveness), and transcript structure. All emitted fields pass
through a two-layer allowlist — raw records contain titles and paths we read
but never emit (tested with exact-key assertions, 16 tests).

## What we verified vs. what we did not

- **Verified**: PID-based dead/alive classification against real sessions;
  resume on a dead session succeeds; resume against a *live* session fails at
  the ACP layer (so the tool refuses it rather than corrupting state); the
  tunnel path works.
- **Not verified**: a real Alexa+ device (demo exercises the same MCP contract
  through a local voice loop); real resume execution stays a dry-run by
  default (`FVO_DRY_RUN=0` opts in); the demo video uses a four-session
  fixture so no private session data appears on screen.

## Built with

Python 3, `mcp` SDK (Streamable HTTP), `devin` CLI + session lock files +
transcripts as data sources, ffmpeg + Piper TTS for the demo video itself.
