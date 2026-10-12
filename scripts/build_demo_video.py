#!/usr/bin/env python3
"""デモ動画の決定論的レンダラー(demo-videoスキル・常法工程の実装)。

画面収録を使わず、シーンを色面+drawtextで生成する — 実端末のスクリーンに
内部情報が映り込む事故を構造的に防ぐ。fixtureツールの実出力をカードに描く。

使い方: python scripts/build_demo_video.py
出力: submit/demo.mp4(180秒以内・検品つき)
依存: ffmpeg / piper-tts(venv) / 音声モデルは ~/.cache/fvo-voices/ に自動DL
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "submit" / "video_build"
FINAL = ROOT / "submit" / "demo.mp4"
VOICE_DIR = Path.home() / ".cache" / "fvo-voices"
VENV_PY = sys.executable

VOICES = {
    "narrator": "en_US-ryan-high",   # ナレーション+デバイス応答(低め男性)
    "user": "en_US-amy-medium",      # ユーザー(キッチンの声)
}

FONT = "/System/Library/Fonts/Helvetica.ttc"
MONO = "/System/Library/Fonts/Menlo.ttc"
W, H = 1280, 720
MAX_TOTAL_S = 180.0
BG = "0x0d1117"      # github-dark系
FG = "white"
ACCENT = "0x58a6ff"  # 青
WARN = "0xf85149"    # 赤
GOOD = "0x3fb950"    # 緑
AMBER = "0xd29922"   # 黄


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd[:6])}...\n{proc.stderr[-800:]}")


def _dur(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def _ensure_voice(name: str) -> Path:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    model = VOICE_DIR / f"{name}.onnx"
    if not model.exists():
        subprocess.run(
            [VENV_PY, "-c",
             f"from piper.download_voices import download_voice; "
             f"from pathlib import Path; download_voice('{name}', Path('{VOICE_DIR}'))"],
            check=True)
    return model


def _tts(text: str, voice: str, out: Path) -> Path:
    model = _ensure_voice(VOICES[voice])
    proc = subprocess.run(
        [VENV_PY, "-m", "piper", "-m", str(model), "-f", str(out)],
        input=text, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"piper failed: {proc.stderr[-400:]}")
    # piper出力の前後無音をトリム(シーン間に3s超の無音が出ないよう締める)
    trimmed = out.with_suffix(".trim.wav")
    _run(["ffmpeg", "-y", "-i", str(out), "-af",
          "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1,"
          "areverse,silenceremove=start_periods=1:start_threshold=-45dB:"
          "start_silence=0.15,areverse",
          str(trimmed)])
    trimmed.replace(out)
    return out


def _concat_audio(parts: list[Path], gap_s: float, out: Path) -> Path:
    """wav群を無音ギャップ付きで連結する。"""
    if not parts:
        raise ValueError("no audio parts")
    # 無音フィラー
    silence = out.parent / "_sil.wav"
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
          "-t", str(gap_s), str(silence)])
    seq: list[Path] = []
    for i, p in enumerate(parts):
        seq.append(p)
        if i < len(parts) - 1:
            seq.append(silence)
    lst = out.parent / "_alist.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in seq))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
          "-ar", "22050", "-ac", "1", str(out)])
    return out


def _scene_video(scene_id: str, dur: float, title_file: Path, body_file: Path | None,
                 accent: str, out: Path) -> Path:
    """1シーンの映像(色面+タイトル+本文)。音声は後でmux。
    drawtextはtext=内のカンマ等でfilterchainが壊れるため全てtextfile経由。"""
    filters = [
        f"drawtext=fontfile={FONT}:textfile='{title_file}':fontsize=44:fontcolor={accent}:"
        f"x=60:y=50",
    ]
    if body_file:
        filters.append(
            f"drawtext=fontfile={MONO}:textfile='{body_file}':fontsize=26:"
            f"fontcolor={FG}:x=60:y=140:line_spacing=14")
    vf = ",".join(filters)
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={BG}:s={W}x{H}:d={dur}",
          "-vf", vf, "-pix_fmt", "yuv420p", str(out)])
    return out


def _mux(video: Path, audio: Path, dur: float, out: Path) -> Path:
    """音声を映像長まで無音パディングしてmux(-shortestは使わない:
    音声が短いと映像が切り詰められて尺が崩れる)。"""
    _run(["ffmpeg", "-y", "-i", str(video), "-i", str(audio),
          "-filter_complex", f"[1:a]apad,atrim=0:{dur}[a]",
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
          str(out)])
    return out


def _fixture_fleet_text() -> str:
    os.environ["FVO_DATA_SOURCE"] = "fixture"
    from fleet_voice_ops.app.tools import fleet_status
    lines = ["$ fleet_status()"]
    for s in fleet_status():
        mark = {"active": "▲", "stalled_suspect": "■", "dead": "✕"}[s["status"]]
        lines.append(
            f"{mark} {s['session_id']:<16} {s['status']:<16} "
            f"elapsed={s['elapsed_s']:>6}s  last={s['last_tool_name']}")
    return "\n".join(lines)


def _fixture_stall_text() -> str:
    os.environ["FVO_DATA_SOURCE"] = "fixture"
    from fleet_voice_ops.app.tools import analyze_stall
    return "$ analyze_stall('demo-birch')\n" + json.dumps(
        analyze_stall("demo-birch"), indent=2, ensure_ascii=False)


def _resume_text() -> str:
    return ("$ request_resume('demo-driftwood', confirm=true)\n"
            "[dry-run] devin --resume demo-driftwood --print please continue")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # シーン定義(demo-script.mdの6シーンに対応)。音声テキストは英語。
    scenes = [
        {
            "id": "01_kitchen",
            "title": "SCENE 1 — Kitchen. No screen in sight.",
            "accent": ACCENT,
            "lines": [
                ("user", "Hey, anything going on with my agents?"),
                ("narrator",
                 "Out of four sessions, one is waiting for input, thirty minutes now. "
                 "And one died with an error. "
                 "You don't need to check your screen to know that."),
            ],
            "body": 'You:     "Hey, anything going on with my agents?"\n\n'
                    "Device:  Out of four sessions, one is waiting\n"
                    "         for input (30 min), and one died\n"
                    "         with an error.",
            "min_dur": 8.0,
        },
        {
            "id": "02_fleet",
            "title": "What it sees: liveness, not conversations",
            "accent": ACCENT,
            "lines": [(
                "narrator",
                "fleet-voice-ops reads session liveness from PID checks and recent "
                "activity timestamps — never what's inside the conversation. "
                "Three states: active, stalled, dead. That's all it emits.")],
            "body": _fixture_fleet_text(),
            "min_dur": 10.0,
        },
        {
            "id": "03_stall",
            "title": "Not just detection — hypotheses with evidence",
            "accent": AMBER,
            "lines": [(
                "narrator",
                "It doesn't just flag a stall. It proposes multiple hypotheses, each "
                "with confidence and the evidence signals behind it — then recommends "
                "one action. Waiting for user input, with high confidence, because the "
                "last tool call was a question.")],
            "body": _fixture_stall_text(),
            "min_dur": 12.0,
        },
        {
            "id": "04_resume",
            "title": "SCENE 4 — Voice approval, no hands",
            "accent": WARN,
            "lines": [
                ("narrator",
                 "demo-driftwood died with an error. It's safe to resume — "
                 "want me to restart it?"),
                ("user", "Yes, go ahead."),
                ("narrator",
                 "Resuming demo-driftwood now. Confirmation required the session name, "
                 "never a number — so a misheard digit can't fire the wrong action."),
            ],
            "body": _resume_text(),
            "min_dur": 9.0,
        },
        {
            "id": "05_boundary",
            "title": "What this demo does NOT do yet",
            "accent": WARN,
            "lines": [(
                "narrator",
                "Honest boundaries. This demo runs on a fixture — the real reader "
                "exists and reads actual session state, but it is not wired to a live "
                "Alexa device yet, and resume stays a dry run. Because we tested it: "
                "a live session rejects re-attach.")],
            "body": "demo shown on fixture data  —  real reader implemented\n"
                    "real Alexa+ device  —  NOT yet verified\n"
                    "real resume execution  —  dry-run only",
            "min_dur": 10.0,
        },
        {
            "id": "06_title",
            "title": "fleet-voice-ops",
            "accent": GOOD,
            "lines": [(
                "narrator",
                "Voice observability for parallel coding agents. "
                "Built as an open MCP server — four tools, three states, "
                "one voice approval. Ask from the kitchen — know without the screen.")],
            "body": "Voice observability for parallel coding agents.\n"
                    "An MCP server for the Alexa+ track.\n"
                    "Amazon Developer Hackathon 2026.",
            "min_dur": 8.0,
        },
    ]

    scene_vids: list[Path] = []
    for sc in scenes:
        # 1. 音声
        parts: list[Path] = []
        for i, (voice, text) in enumerate(sc["lines"]):
            parts.append(_tts(text, voice, OUT_DIR / f"{sc['id']}_l{i}.wav"))
        audio = _concat_audio(parts, 0.55, OUT_DIR / f"{sc['id']}.wav")
        dur = max(_dur(audio) + 1.2, sc["min_dur"])

        # 2. テキストファイル(drawtextはtextfile経由でエスケープ不要に)
        title_file = OUT_DIR / f"{sc['id']}_title.txt"
        title_file.write_text(sc["title"])
        body_file = None
        if sc["body"]:
            body_file = OUT_DIR / f"{sc['id']}_body.txt"
            body_file.write_text(sc["body"])

        # 3. 映像+音声mux
        vid = _scene_video(sc["id"], dur, title_file, body_file, sc["accent"],
                           OUT_DIR / f"{sc['id']}_v.mp4")
        scene_vids.append(_mux(vid, audio, dur, OUT_DIR / f"{sc['id']}.mp4"))
        print(f"scene {sc['id']}: {dur:.1f}s")

    # 4. 連結
    lst = OUT_DIR / "_scenes.txt"
    lst.write_text("".join(f"file '{v}'\n" for v in scene_vids))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
          "-c", "copy", str(FINAL)])

    total = _dur(FINAL)
    print(f"TOTAL: {total:.1f}s -> {FINAL}")
    if total > MAX_TOTAL_S:
        print(f"NG: over {MAX_TOTAL_S}s limit")
        return 1

    # 5. 検品
    verify = Path.home() / ".agents/skills/demo-video/scripts/verify_video.sh"
    if verify.exists():
        proc = subprocess.run(["bash", str(verify), str(FINAL), "180", "60"],
                              capture_output=True, text=True)
        print(proc.stdout)
        return proc.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
