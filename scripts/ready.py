#!/usr/bin/env python3
"""提出前 readiness gate — 「ファイルに配線があるか」「引用したテストが実際に通るか」を機械チェックする。

使い方:
  python3 scripts/ready.py               # フルチェック(本番URLへのliveプローブを含む・要設定)
  python3 scripts/ready.py --skip-live   # liveプローブを飛ばす(オフライン開発中)

3状態:
  - pass / fail: 加重%に加算される自動採点対象
  - user_gated : 機械確認不能・提出前に人間が目で見て確認する項目(スコアに含まない)

注意: 生成直後の状態では submit/demo.mp4 等が存在しないため、このゲートは意図的に赤になる。
これは失敗ではなく「提出までのTODOを表示する」ためのデフォルト状態。
(2026-09-27追加: 提出物プロジェクト向け足場・sagi-shield/Archon readinessパターン由来)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THRESHOLD = 90.0
LIVE_HEALTH_URL = ""  # デプロイ後にここへ本番URLの health/root エンドポイントを設定する
VIDEO_URL = "https://youtu.be/kPtD3aMYqDE"  # YouTube公開版の提出動画(2026-10-13)

SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"ya29\.[0-9A-Za-z_\-]+"),
    re.compile(r"sk-[0-9A-Za-z]{20,}"),
]

# SPEC §プライバシー境界5: 公開物grepゲート(会社固有名詞)。
# 禁止語自体が公開物に書けない(語そのものが社内情報)ため、
# リストはローカル設定ファイルから読む — 無ければfail-closedでNGにする。
def _load_company_patterns() -> list[re.Pattern]:
    path = Path(
        os.environ.get(
            "FVO_FORBIDDEN_TERMS",
            Path.home() / ".config" / "fleet-voice-ops" / "forbidden_terms.txt",
        )
    )
    if not path.exists():
        return []
    return [
        re.compile(line.strip(), re.IGNORECASE)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

DEMO_SCRIPT_SECTION_HEADERS = ["## 尺・構成", "## シーン一覧", "## 撮影・生成手順"]


@dataclass
class CheckResult:
    name: str
    weight: float
    status: str  # "pass" | "fail" | "skip" | "user_gated"
    detail: str = ""


@dataclass
class Report:
    results: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, weight: float, ok: bool, detail: str = "") -> None:
        self.results.append(CheckResult(name, weight, "pass" if ok else "fail", detail))

    def add_skip(self, name: str, weight: float, detail: str = "") -> None:
        self.results.append(CheckResult(name, weight, "skip", detail))

    def add_gated(self, name: str, detail: str = "") -> None:
        self.results.append(CheckResult(name, 0.0, "user_gated", detail))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


# ---- 提出物の存在 ----

def check_description(report: Report) -> None:
    p = ROOT / "submit" / "description.md"
    ok = p.exists() and p.stat().st_size > 0
    report.add("submit/description.md 存在", 15, ok, str(p) if ok else "見つかりません")


def check_demo_mp4(report: Report) -> None:
    p = ROOT / "submit" / "demo.mp4"
    ok = p.exists() and p.stat().st_size > 0
    report.add("submit/demo.mp4 存在", 15, ok, str(p) if ok else "見つかりません(デモ動画は未生成)")


# ---- 検証(scripts/verify があれば実行) ----

def check_verify(report: Report) -> None:
    name = "scripts/verify (存在すれば実行して確認)"
    verify = ROOT / "scripts" / "verify"
    if not verify.exists():
        report.add_skip(name, 40, "scripts/verify が無い(プロジェクトの技術スタックに合わせて用意すること)")
        return

    try:
        cmd = [str(verify)] if verify.stat().st_mode & 0o111 else ["bash", str(verify)]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        ok = proc.returncode == 0
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-3:])
        detail = tail if tail else f"exit={proc.returncode}"
    except subprocess.TimeoutExpired:
        ok = False
        detail = "scripts/verify が180秒でタイムアウト"
    except Exception as e:  # noqa: BLE001
        ok = False
        detail = f"実行失敗: {e}"

    report.add(name, 40, ok, detail)


# ---- README ----

def check_readme_ship(report: Report) -> None:
    readme = read_text(ROOT / "README.md")
    ok = "Ship対象:" in readme
    report.add("README.md にShip対象の記述", 10, ok)


# ---- 秘密情報 ----

def _tracked_files() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True, timeout=15, check=True,
        )
        return [l for l in out.stdout.splitlines() if l]
    except Exception:
        return []


def check_no_secrets_in_tracked_files(report: Report) -> None:
    files = _tracked_files()
    hits: list[str] = []
    binary_exts = {".png", ".jpg", ".jpeg", ".mp4", ".mov", ".ico", ".woff", ".woff2", ".gif"}
    for rel in files:
        p = ROOT / rel
        if p.suffix.lower() in binary_exts or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                hits.append(rel)
                break
    ok = not hits
    report.add("追跡ファイルに実キー形式の秘密情報が無い", 10, ok, "" if ok else f"検出: {', '.join(hits[:5])}")


def check_env_not_tracked(report: Report) -> None:
    files = set(_tracked_files())
    tracked_env = [f for f in files if Path(f).name == ".env" or Path(f).name.startswith(".env.")]
    ok = not tracked_env
    report.add(".env がgit追跡されていない", 10, ok, "" if ok else f"追跡中: {', '.join(tracked_env)}")


# ---- SPEC-initial.md §作業順序5: 作業順序逆転の機械強制 ----

def check_demo_script_sections_filled(report: Report) -> None:
    """submit/demo-script.md の各節(尺・構成/シーン一覧/撮影・生成手順)が空でないこと。"""
    name = "submit/demo-script.md 各節が空でない"
    text = read_text(ROOT / "submit" / "demo-script.md")
    if not text:
        report.add(name, 15, False, "submit/demo-script.md が見つからないか空")
        return

    lines = text.splitlines()
    header_positions = [i for i, line in enumerate(lines) if line.strip() in DEMO_SCRIPT_SECTION_HEADERS]
    missing_headers = [h for h in DEMO_SCRIPT_SECTION_HEADERS if h not in text]
    if missing_headers:
        report.add(name, 15, False, f"見出しが無い: {', '.join(missing_headers)}")
        return

    empty_sections: list[str] = []
    for idx, pos in enumerate(header_positions):
        header = lines[pos].strip()
        end = header_positions[idx + 1] if idx + 1 < len(header_positions) else len(lines)
        body = "\n".join(lines[pos + 1 : end]).strip()
        if not body:
            empty_sections.append(header)

    ok = not empty_sections
    report.add(name, 15, ok, "" if ok else f"本文が空の節: {', '.join(empty_sections)}")


def check_voice_round_trip_smoke(report: Report) -> None:
    """fixtureデータで音声1往復(質問→応答)がエラーなく成立すること。"""
    name = "fixture音声1往復のスモークテスト"
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.path.insert(0, 'scripts'); sys.path.insert(0, '.'); "
                "from voice_demo import handle_question; "
                "reply1, sid = handle_question('\u4f55\u304b\u3042\u3063\u305f?', None); "
                "assert sid, 'stalled_suspect\u304c\u691c\u51fa\u3055\u308c\u306a\u3044'; "
                "reply2, sid2 = handle_question('\u304a\u9858\u3044', sid); "
                "assert 'dry-run' in reply2 or 'devin' in reply2, reply2; "
                "print('OK')"
            ),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    ok = proc.returncode == 0 and "OK" in proc.stdout
    detail = "" if ok else f"stdout={proc.stdout.strip()[-200:]} stderr={proc.stderr.strip()[-200:]}"
    report.add(name, 15, ok, detail)


def check_no_company_names(report: Report) -> None:
    """公開物grepゲート: 会社固有名詞がgit追跡ファイル+submit/+fixtureに無いこと(ヒット1件でFAIL)。"""
    name = "会社固有名詞grep ヒット0"
    targets = set(_tracked_files())
    for extra_dir in ("submit", "fleet_voice_ops"):
        d = ROOT / extra_dir
        if d.exists():
            for p in d.rglob("*"):
                if p.is_file():
                    try:
                        targets.add(str(p.relative_to(ROOT)))
                    except ValueError:
                        continue

    patterns = _load_company_patterns()
    if not patterns:
        report.add(name, 15, False, "禁止語設定ファイルが無い(fail-closed): ~/.config/fleet-voice-ops/forbidden_terms.txt")
        return

    binary_exts = {".png", ".jpg", ".jpeg", ".mp4", ".mov", ".ico", ".woff", ".woff2", ".gif"}
    # このファイル自身は走査対象から外す(パターンは外部化したが念のため)
    self_rel = str(Path(__file__).resolve().relative_to(ROOT))
    hits: list[str] = []
    for rel in sorted(targets):
        if rel == self_rel:
            continue
        p = ROOT / rel
        if p.suffix.lower() in binary_exts or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat.search(text):
                hits.append(rel)
                break

    ok = not hits
    report.add(name, 15, ok, "" if ok else f"検出: {', '.join(hits[:10])}")


# ---- user_gated(スコア外・機械確認不能/人間確認が必要) ----

def add_manual_gates(report: Report, skip_live: bool) -> None:
    if skip_live:
        report.add_gated("本番デプロイURL", "--skip-live のためプローブせず。人間が確認")
    elif not LIVE_HEALTH_URL:
        report.add_gated("本番デプロイURL", "LIVE_HEALTH_URL未設定。デプロイ後にこのファイルへURLを設定し人間が確認")
    else:
        report.add_gated("本番デプロイURL", f"{LIVE_HEALTH_URL} — 到達性を人間が確認")
    if VIDEO_URL:
        report.add_gated("動画アップロード", f"{VIDEO_URL} — public再生できるか人間が確認")
    else:
        report.add_gated("動画アップロード", "submit/demo.mp4 を要求経路(YouTube等)へアップロードしURLを登録したか人間が確認")
    report.add_gated("提出フォーム送信", "提出フォーム・ダッシュボードから送信したか人間が確認")


# ---- レポート ----

def run(skip_live: bool) -> int:
    report = Report()

    check_description(report)
    check_demo_mp4(report)
    check_verify(report)
    check_readme_ship(report)
    check_no_secrets_in_tracked_files(report)
    check_env_not_tracked(report)
    check_demo_script_sections_filled(report)
    check_voice_round_trip_smoke(report)
    check_no_company_names(report)

    add_manual_gates(report, skip_live)

    scored = [r for r in report.results if r.status in ("pass", "fail")]
    gated = [r for r in report.results if r.status == "user_gated"]
    skipped = [r for r in report.results if r.status == "skip"]

    total_weight = sum(r.weight for r in scored)
    earned_weight = sum(r.weight for r in scored if r.status == "pass")
    score = (earned_weight / total_weight * 100.0) if total_weight else 0.0
    any_fail = any(r.status == "fail" for r in scored)

    print("=== 提出前 readiness ===\n")
    print("[自動採点]")
    for r in scored:
        mark = "OK " if r.status == "pass" else "NG "
        print(f"  {mark} ({r.weight:>4.1f}%) {r.name}" + (f" — {r.detail}" if r.detail else ""))

    if skipped:
        print("\n[skip(判定不能・スコア対象外)]")
        for r in skipped:
            print(f"  -- {r.name} — {r.detail}")

    print("\n[user_gated — 人間が確認する項目・スコア外]")
    for r in gated:
        print(f"  ?? {r.name} — {r.detail}")

    print(f"\n加重スコア: {score:.1f}% (閾値 {THRESHOLD:.0f}%) / 加算対象={len(scored)}件 skip={len(skipped)}件 user_gated={len(gated)}件")

    passed = score >= THRESHOLD and not any_fail
    print("判定: " + ("PASS" if passed else "FAIL"))
    return 0 if passed else 1


def main(argv: list[str]) -> int:
    skip_live = "--skip-live" in argv
    return run(skip_live)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
