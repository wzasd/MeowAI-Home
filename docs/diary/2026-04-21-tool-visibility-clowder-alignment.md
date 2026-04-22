---
created: 2026-04-21
topics: [tool-visibility, frontend, clowder-alignment]
---

# Tool Visibility Rail 对齐 Clowder 实现

## 背景

铲屎官反馈 ToolRail 显示效果不佳，要求参考 clowder 的实现方式。

## 改动

### 1. 修复占位文字重复显示

**问题**: `ChatArea.tsx` 中"这只猫正在赶来，消息马上到。|"在 ToolRail 显示时仍然出现。

**修复**: 移除 tools-only 渲染块中的占位 div，只保留 ToolRail。

### 2. 布局对齐 Clowder

**问题**: ToolRail 放在消息气泡外面（上面），和 clowder 不一致。

**Clowder 布局**:
```
[AgentBadge]
[消息气泡]
  ├── [回复内容]
  └── [CliOutputBlock]  ← 在气泡内部
```

**修复**: 把 ToolRail 移到消息气泡内部（`nest-card` 内），和回复内容在一起。

**文件**: `web/src/components/chat/ChatArea.tsx:277-310`

### 3. 样式完全重写

**参考**: `clowder-ai/packages/web/src/components/cli-output/CliOutputBlock.tsx`

**样式对齐点**:
- 深色背景 - `tintedDark()` 函数生成猫品种色调的深色背景
- Header 结构 - chevron(accent色) + summary + 右侧状态计数
- Tool Row - `[status icon] [wrench] [label] [duration] [expand]`
- Active 状态 - 左边框 2px + 背景 20% 透明度
- 可折叠 - 点击 header 展开/收起
- 字体 - `font-mono text-[11px]` 与 clowder 一致
- 颜色系统 - `accentLight` / `accentVeryLight` 渐变

**新增函数** (从 clowder 移植):
- `hexToRgba()` - hex 转 rgba
- `tintedDark()` - 深色背景混合
- `lighten()` - 颜色提亮
- `extractPrimaryArg()` - 从 JSON detail 提取主要参数
- `truncateArg()` - 截断长参数
- `cleanToolName()` - 清理 "catId → ToolName" 格式

**新增图标** (SVG 内联):
- `ChevronIcon` - 展开/折叠箭头
- `WrenchIcon` - 扳手图标
- `CheckIcon` - 完成勾选
- `LoaderIcon` - 加载动画

## 验证

1. `npx tsc --noEmit` 通过
2. 刷新页面测试工具调用显示

## 后续

- 考虑统一 transient (ToolRail) 和 persistent (CliOutputBlock) 的显示风格
- 添加 breedColor prop 传递猫品种颜色
