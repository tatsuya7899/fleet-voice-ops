# fleet-voice-ops

## 📚 Knowledge
知見はこのリポジトリ内に置く: 仕様=SPEC-*.md / 構想=IDEA-*.md / 決定記録=DEC-*.md(Studio憲法・命名規則)。
Studio全体の横断閲覧は Obsidian で ~/Developer を直接開く(別Vaultは作らない)。

## 🚀 Quick Start

```bash
# Development
npm run dev

# Build
npm run build

# Test
npm test
```

## 🔁 開発フロー
非自明な機能は `_ops/docs/strategy/AI_DRIVEN_DEV_PRACTICAL_FLOW_20260905.md` の8ステップ(プラン→AI相互レビュー×2→実装→テスト→AI相互レビュー→人間レビュー→定期リファクタリング)に沿う。
並列でAIに大きな変更を試させるときは `git worktree` でブランチごと作業空間を分離する。

## 📝 Development Notes
非自明な学びは _ops/lessons/ へ(R5)。
