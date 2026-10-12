# fleet-voice-ops

**このファイルは地図に徹する。詳細を書き込まない。**(`_ops/docs/strategy/AI_DRIVEN_DEV_PRACTICAL_FLOW_20260905.md` 1-1節準拠)

## 技術スタックの要約
Python(venv)

## ディレクトリ構成
- `venv/` — 仮想環境(gitignore対象・直接編集しない)
- `requirements.txt` — 依存関係

## 主要コマンド
```bash
source venv/bin/activate  # 仮想環境を有効化
pip install -r requirements.txt
pytest                    # テスト実行
```

## 開発ルールへの誘導
詳細な作業規則は、対象ディレクトリの `AGENTS.md` を参照する。Claude Code固有の補助規則は `.claude/rules/` に置く。
仕様は `SPEC-initial.md`、学びは Studio 全体の `_ops/lessons/` へ(R5)。
