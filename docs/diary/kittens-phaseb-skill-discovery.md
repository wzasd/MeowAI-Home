# Phase B: Skill 自动发现与同步

## 完成内容

### 后端
- `src/capabilities/discovery.py` 新增 `SkillMeta`、`discover_skills()`、`read_skill_meta()`、`read_manifest_meta()`
  - 扫描项目级 `skills/` 目录，识别包含 `SKILL.md` 的子目录
  - 解析 `SKILL.md` YAML frontmatter 提取 `description` 和 `triggers`
  - 读取 `skills/manifest.yaml` 作为元数据补充来源，优先级高于 SKILL.md
  - 修复了 `content.match()` 错误，改为 `re.match()`
- `src/capabilities/orchestrator.py` 新增 `sync_skills()`
  - 自动将发现的 skill 同步进 `.neowai/capabilities.json`
  - 添加新 skill（默认 enabled=True）
  - 更新已有 skill 的 description/triggers，保留 enabled 和 per-cat overrides
  - 自动清理文件系统中已不存在的 skill
  - 修复了 `None` 与 `[]` 的 triggers 比较导致误写的问题
- `src/capabilities/bootstrap.py` 在初始化 capabilities.json 时集成 `discover_skills()`，确保首次生成即包含项目级 skills
- `src/capabilities/models.py` 的 `CapabilityEntry` 和 `CapabilityBoardItem` 已预留 `triggers` 字段

### 前端
- `web/src/types/index.ts` 的 `CapabilityBoardItem` 已包含 `triggers?: string[]`
- `web/src/components/settings/CapabilityBoard.tsx` 在 skill 行中以 amber tag 形式展示 triggers

### 测试
- `tests/capabilities/test_orchestrator.py` 新增 10 个测试：
  - `test_discover_skills_reads_frontmatter`
  - `test_discover_skills_uses_manifest`
  - `test_read_skill_meta_no_frontmatter`
  - `test_read_manifest_meta_invalid_skills_type`
  - `test_sync_skills_adds_new`
  - `test_sync_skills_updates_meta`
  - `test_sync_skills_prunes_stale`
  - `test_sync_skills_no_changes`
  - `test_capability_board_includes_triggers`
- `tests/web/test_capabilities_api.py` 新增 `test_get_capabilities_includes_skills`

## 验证结果
- Python 测试：31/31 通过
- 前端 TypeScript：`tsc --noEmit` 零错误

## 关键修复
- `discovery.py` 中 `content.match()` 不存在，改为 `re.match()`
- `sync_skills()` 中 `cap.triggers` 为 `None` 时与 `meta.triggers` 为 `[]` 的比较产生误写，已规范化为 `(cap.triggers or []) != (meta.triggers or [])`
