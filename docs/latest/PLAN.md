# SkillPort 中期成長戦略

> **作成日**: 2025-12-11
> **対象期間**: 2025年12月 - 2026年12月（12ヶ月）
> **ステータス**: Draft

## Executive Summary

SkillPortは「MCPエコシステムにおけるスキル管理の標準ツール」としてのポジションを確立する。2025年12月のMCPのLinux Foundation（AAIF）への寄贈、OpenAI/Google/Microsoftによる採用加速という市場環境の変化を機会と捉え、既存の強み（プライバシー、シンプルさ、Claude Skills互換）を維持しながら、エコシステム統合とエンタープライズ機能で差別化を図る。

---

## 1. 環境分析

### 1.1 外部環境（MCP/Agentエコシステム 2025年末時点）

#### 市場動向
| 指標 | 数値 | 出典 |
|------|------|------|
| AI Agent市場規模（2024） | $5.4-5.9B | GMInsights |
| AI Agent市場規模（2034予測） | $105.6B | CAGR 38.5% |
| Fortune 500のMCP採用率 | 28%（2025 Q1） | 前年比+16pt |
| MCP SDK月間ダウンロード数 | 97M+ | Python+TS |

#### 重要なエコシステム変化（2025年）
1. **MCP標準化**: Anthropic → Linux Foundation/AAIF（2025年12月）
2. **大手採用**: OpenAI（3月）、Google DeepMind（4月）、Microsoft（5月）
3. **MCP Registry**: 公式レジストリローンチ（9月）、API安定化（10月）
4. **Claude Code Plugins**: Skills/Commands/Hooks/MCPをバンドル可能に（11月）
5. **セキュリティ強化**: OAuth 2.0必須化、Elicitations機能（6月仕様）

#### 競合環境
| カテゴリ | 主要プレイヤー | SkillPortとの関係 |
|----------|---------------|------------------|
| Agent Framework | LangChain, CrewAI, AutoGen | 補完可能（統合対象）|
| Enterprise Platform | Salesforce, ServiceNow, IBM | 異なるセグメント |
| Claude Native | Claude Code Skills | 互換（差別化必要）|
| MCP Server管理 | MCP Registry | 統合対象 |

### 1.2 内部環境（SkillPort v0.4.0時点）

#### 強み
- Claude Agent Skills**完全互換**
- MCP Server + CLI**両立**（柔軟な導入）
- **プライバシー重視**のBM25検索（API不要）
- **プログレッシブディスクロージャー**（100skills≈15K tokens）
- **マルチクライアントフィルタリング**（env変数ベース）
- LanceDB（Vector + FTS統合）、シンプルなアーキテクチャ

#### 弱み/制約
- 中央レジストリなし（発見性の欠如）
- コミュニティ規模が小さい（認知度）
- エンタープライズ機能不足（監査、RBAC）
- HTTPモードが実験的
- セマンティック検索にOpenAI API必要

### 1.3 SWOT分析サマリー

```
           内部要因
    ┌─────────────────────┐
    │  強み    │   弱み   │
    │ 互換性   │ 発見性   │
外  │ プライバ │ コミュニ │
部  │ シー重視 │ ティ規模 │
要  ├─────────┼──────────┤
因  │  機会    │   脅威   │
    │ MCP標準化│ Claude   │
    │ Registry │ Native進化│
    │ Plugin化 │ 大手内製 │
    └─────────────────────┘
```

---

## 2. 戦略方針

### 2.1 ポジショニング

**「MCPエコシステムにおけるスキル管理の標準ツール」**

- **Who**: MCP対応AIツール（Cursor, Copilot, Codex等）を使うチーム/開発者
- **What**: スキルの一元管理・配信・検索
- **Why**: コンテキスト効率化、マルチクライアント対応、プライバシー保護

### 2.2 競争優位の源泉

| 差別化軸 | 現在 | 目標 |
|----------|------|------|
| Claude Skills互換 | 完全 | 維持 |
| プライバシー | API不要FTS | ローカル埋め込み追加 |
| エコシステム統合 | 独立 | Registry/Plugin連携 |
| エンタープライズ | なし | 監査/フィルタリング |

### 2.3 設計原則（維持）

1. **Convention Over Configuration** - デフォルトで動作
2. **Progressive Complexity** - 段階的な機能開放
3. **Portable Format** - Anthropic Skills形式準拠
4. **Searchable by Default** - FTSファーストのフォールバック

---

## 3. フェーズ別ロードマップ

### Phase 1: エコシステム統合（0-3ヶ月）

**目標**: MCP公式エコシステムとの接続確立

#### 3.1.1 MCP Registry統合
- [ ] 公式MCP Registryへの登録申請
- [ ] `.well-known/mcp.json` エンドポイント対応
- [ ] メタデータスキーマの標準準拠確認
- [ ] Discovery機能の実装（外部レジストリからのスキル検索）

#### 3.1.2 Claude Code Plugin化
- [ ] Plugin構造の作成（skills/ + commands/ + mcp.json）
- [ ] `/plugin install skillport` 対応
- [ ] claude-code-plugins-plus への登録
- [ ] Skills Marketplace（skillsmp.com）への掲載

#### 3.1.3 配布改善
- [ ] 公式Dockerイメージ（`ghcr.io/gotalab/skillport`）
- [ ] docker-compose.yml サンプル
- [ ] Homebrew Formula（macOS向け）

#### 3.1.4 Transport安定化
- [ ] Streamable HTTP Transport対応（SSE廃止準備）
- [ ] HTTPモードのテスト強化
- [ ] リモートエージェント向けドキュメント

### Phase 2: 機能拡張（3-6ヶ月）

**目標**: エンタープライズ/チーム向け機能強化

#### 3.2.1 レジストリ連携
- [ ] GitHub MCP Registry統合（`skillport add registry:<name>`）
- [ ] 外部レジストリからのインストール対応
- [ ] 組織内レジストリのフェデレーション

#### 3.2.2 セキュリティ強化
- [ ] OAuth 2.0サポート（リモートスキルソース認証）
- [ ] スキル署名・検証機能（GPG/cosign）
- [ ] 権限アノテーション（readOnlyHint, destructiveHint）
- [ ] 脆弱性スキャン統合（依存関係チェック）

#### 3.2.3 エンタープライズ機能
- [ ] 監査ログ（JSON Lines形式、誰が何をいつ）
- [ ] Allowlist/Blocklist機能強化
- [ ] チームnamespace管理（RBAC準備）
- [ ] 使用統計エクスポート

#### 3.2.4 開発者体験向上
- [ ] ホットリロード（`--watch`モード、開発時のみ）
- [ ] `skillport create` テンプレートジェネレーター
- [ ] バリデーション強化（schema定義、CI連携）
- [ ] VS Code拡張（Skill.md編集支援）

### Phase 3: 差別化・拡張（6-12ヶ月）

**目標**: 次世代エージェント環境への対応

#### 3.3.1 Multi-Agent対応
- [ ] エージェント間スキル共有プロトコル設計
- [ ] Orchestrator向けAPI（スキル推薦、コンテキスト最適化）
- [ ] 協調実行のサポート（ロック、状態共有）

#### 3.3.2 Observability統合
- [ ] OpenTelemetry対応（トレース、メトリクス）
- [ ] LangSmith/LangFuse連携オプション
- [ ] スキル使用状況ダッシュボード
- [ ] パフォーマンスプロファイリング

#### 3.3.3 セマンティック検索強化
- [ ] ローカル埋め込みモデル対応（sentence-transformers）
- [ ] ハイブリッド検索（Vector + BM25）の最適化
- [ ] 多言語スキル対応（i18n）

#### 3.3.4 エコシステム拡張
- [ ] LangChain Tool化（`SkillPortToolkit`）
- [ ] CrewAI Agent連携
- [ ] カスタムトランスポートAPI

---

## 4. 優先度マトリクス

### 4.1 Impact vs Effort

```
High Impact
    │
    │  ★ Registry統合    ★ Plugin化
    │  ★ Docker配布
    │
    │         ○ OAuth 2.0
    │         ○ 監査ログ
    │
    │                   △ Multi-Agent
    │                   △ Observability
    │
    └────────────────────────────────────
                                    High Effort

★ Phase 1 (Quick Wins)
○ Phase 2 (Strategic)
△ Phase 3 (Long-term)
```

### 4.2 優先順位（Phase 1詳細）

| # | タスク | 重要度 | 工数 | 依存 |
|---|--------|--------|------|------|
| 1 | Claude Code Plugin化 | 高 | 中 | なし |
| 2 | MCP Registry登録 | 高 | 低 | なし |
| 3 | Dockerイメージ | 中 | 低 | なし |
| 4 | Streamable HTTP | 中 | 中 | HTTPモード |

---

## 5. 成功指標（KPI）

### 5.1 Adoption Metrics

| 指標 | 現在 | 3ヶ月目標 | 12ヶ月目標 |
|------|------|-----------|------------|
| PyPI月間ダウンロード | N/A | 500 | 5,000 |
| GitHub Stars | ~10 | 100 | 1,000 |
| 登録レジストリ数 | 0 | 2 | 5 |
| Plugin Marketplace掲載 | 0 | 1 | 3 |

### 5.2 Quality Metrics

| 指標 | 現在 | 目標 |
|------|------|------|
| テストカバレッジ | ~60% | 80% |
| MCP仕様準拠 | 部分的 | 完全 |
| セキュリティ監査 | なし | 年1回 |

### 5.3 Community Metrics

| 指標 | 現在 | 目標 |
|------|------|------|
| Contributors | 1 | 10+ |
| 公開スキル数（連携先） | - | 100+ |
| ドキュメント言語 | EN | EN+JP |

---

## 6. リスクと対策

### 6.1 技術リスク

| リスク | 影響 | 確率 | 対策 |
|--------|------|------|------|
| MCP仕様の破壊的変更 | 高 | 中 | AAIF参加、早期追従 |
| Claude Code内製機能の競合 | 中 | 高 | 差別化（マルチクライアント）維持 |
| LanceDB非互換アップデート | 中 | 低 | バージョン固定、移行パス準備 |

### 6.2 市場リスク

| リスク | 影響 | 確率 | 対策 |
|--------|------|------|------|
| 大手による類似ツール投入 | 高 | 中 | エコシステム統合で先行、OSS優位性 |
| MCP Registry機能重複 | 中 | 中 | ローカル管理+検索の差別化 |
| Agent市場の成長鈍化 | 高 | 低 | 複数クライアント対応で分散 |

### 6.3 リソースリスク

| リスク | 影響 | 確率 | 対策 |
|--------|------|------|------|
| 開発リソース不足 | 高 | 高 | Phase優先度厳守、コミュニティ育成 |
| メンテナンス負荷増大 | 中 | 中 | 自動化、CI/CD強化 |

---

## 7. 次のアクション

### 即時（今週）
- [ ] MCP Registry登録申請の準備
- [ ] Claude Code Plugin構造の調査・設計
- [ ] GitHub Actions: Docker build追加

### 短期（1ヶ月以内）
- [ ] Phase 1タスクの詳細見積もり
- [ ] Plugin構造のプロトタイプ
- [ ] Registry互換性テスト

### 定期レビュー
- **週次**: タスク進捗確認
- **月次**: KPIレビュー、優先度調整
- **四半期**: 戦略見直し

---

## 8. 参考資料

### 8.1 エコシステム
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Registry](https://registry.modelcontextprotocol.io/)
- [Agentic AI Foundation](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
- [Claude Code Plugins](https://www.anthropic.com/news/claude-code-plugins)

### 8.2 競合分析
- [LangChain](https://www.langchain.com/)
- [CrewAI](https://www.crewai.com/)
- [Skills Marketplace](https://skillsmp.com/)

### 8.3 技術仕様
- [MCP Server Development Best Practices](https://modelcontextprotocol.info/docs/best-practices/)
- [Anthropic MCP Directory Policy](https://support.anthropic.com/en/articles/11697096-anthropic-mcp-directory-policy)

---

## Changelog

| 日付 | 変更内容 | 担当 |
|------|----------|------|
| 2025-12-11 | 初版作成 | Claude |
