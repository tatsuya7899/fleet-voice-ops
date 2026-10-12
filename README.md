> Ship対象: Amazon Developer Hackathon "Build, Ship, Shape" Alexa+トラックへの提出物(公開repo+3分英語デモ・締切2026-10-23)

# fleet-voice-ops

**Voice observability for parallel coding agents.** An MCP server that lets you
ask "anything going on?" from the kitchen and hear which agent sessions are
active, stalled, or dead — then approve a safe resume by voice. No screen
required.

Built for the Alexa+ track of the Amazon Developer Hackathon ("Build, Ship,
Shape").

## What it does

- Reads session liveness from PID lock files (`os.kill(pid, 0)`) and
  last-activity timestamps — **never conversation contents**. Emitted fields
  pass a two-layer allowlist enforced by exact-key tests.
- Classifies each session: `active` / `stalled_suspect` / `dead`.
- `analyze_stall` proposes multiple hypotheses with confidence and evidence
  signals, plus one recommended action.
- `request_resume` is guarded by voice approval: confirmation requires the
  session name, never a number. Live sessions are refused (measured: ACP
  re-attach fails); resume stays a dry-run by default (`FVO_DRY_RUN=0` opts in).

## MCP tools

| tool | what it answers |
|---|---|
| `fleet_status` | per-session liveness table (allowlisted keys only) |
| `whats_stuck` | one spoken sentence: what's waiting / what died |
| `analyze_stall` | ranked hypotheses + recommended action |
| `request_resume` | confirmation → dry-run or resume of a dead session |

## Quickstart

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# fixture voice loop (no real sessions needed)
python scripts/voice_demo.py "anything going on?"

# MCP server (Streamable HTTP)
python -m fleet_voice_ops.app.server

# tests
python -m pytest
```

The repo ships a four-session fixture (`FVO_DATA_SOURCE=fixture`, default) so
the demo reproduces without touching real sessions. The real reader switches
on via `FVO_DATA_SOURCE=real`.

## Demo video

`submit/demo.mp4` (~83s, English). Regenerate with:

```bash
pip install piper-tts   # local neural TTS
python scripts/build_demo_video.py   # renders scenes + verifies output
```

## Verified vs. not verified

- **Verified**: PID dead/alive classification on real sessions; resume on a
  dead session; resume refusal on a live session; Bearer-auth'd MCP round-trip
  through an ngrok tunnel; 16 tests.
- **Not verified**: a real Alexa+ device; live transcript reading in the video
  (fixture used so no private data appears on screen); real resume execution.

## License

MIT — see `LICENSE`.
