# Day 2: 三猫协作的架构实现

## 今日目标

让阿橘、墨点、花花三只猫真正协作起来！

具体来说：
1. 实现配置驱动的多猫架构（cat-config.json）
2. 实现角色路由系统（AgentRouter）
3. 真实的 CLI 调用（不再是 Mock）
4. 完整的测试覆盖

## 核心成果

### 1. 配置驱动的猫猫架构

最大的变化是引入了 `cat-config.json`，把三只猫的配置完全外化：

```json
{
  "version": 2,
  "breeds": [
    {
      "id": "orange",
      "name": "橘猫",
      "displayName": "阿橘",
      "roles": ["developer", "coder", "implementer"],
      "mentionPatterns": ["@dev", "@developer", "@coder", "@阿橘", "@orange"],
      "personality": "热情话唠、点子多、有点皮但靠谱",
      "cli": {
        "command": "claude",
        "outputFormat": "stream-json",
        "defaultArgs": ["--output-format", "stream-json"]
      }
    },
    // ... 墨点（奶牛猫）和花花（三花猫）
  ]
}
```

**为什么这么做？**

最初把配置硬编码在代码里，但很快发现问题：
- 每次调整猫的性格都要改代码
- 无法在运行时动态调整
- 难以支持用户自定义猫猫

**设计理念**：Data > Code

配置文件让非程序员也能调整猫猫，更重要的是——让系统更灵活。

### 2. AgentRouter：角色路由系统

这是今天的核心突破！`AgentRouter` 实现了智能的消息路由：

```python
class AgentRouter:
    def route_message(self, message: str) -> List[Dict[str, Any]]:
        """Route message to agents based on @mentions"""
        mentions = self.parse_mentions(message)

        # 1. 提取 @mentions
        # 2. 角色映射（@dev -> orange）
        # 3. 名称匹配（@阿橘 -> orange）
        # 4. 去重并返回服务实例
```

**核心特性**：
- **角色路由**：`@dev` → 橘猫，`@review` → 墨点，`@research` → 花花
- **名称路由**：`@阿橘`、`@墨点`、`@花花` 都能识别
- **多猫协作**：`@dev and @review` 会同时唤醒两只猫
- **默认路由**：没有 @mention 时默认找橘猫

**实现亮点**：

```python
ROLE_TO_BREED = {
    # Development -> Orange
    "developer": "orange",
    "coder": "orange",
    "implementer": "orange",

    # Review -> Inky
    "reviewer": "inky",
    "audit": "inky",
    "inspector": "inky",

    # Research -> Patch
    "researcher": "patch",
    "designer": "patch",
    "creative": "patch",
}
```

这个映射表让系统既支持角色（`@dev`），也支持别名（`@coder`）。

### 3. 真实 CLI 调用（临时文件方案）

Day 1 的 `OrangeService` 只是 Mock，今天实现了真实的 CLI 调用！

**核心挑战**：如何传递 system prompt？

Claude CLI 不支持直接传 system prompt 参数，我们的方案：

```python
async def chat_stream(self, message: str, system_prompt: Optional[str] = None):
    # 1. 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', delete=False, encoding='utf-8'
    )
    temp_file.write(system_prompt)
    temp_file.close()

    try:
        # 2. 构建 CLI 命令
        cmd = self.cli_config["command"]
        args = self.cli_config.get("defaultArgs", []).copy()
        args.extend([
            "--append-system-prompt-file", temp_file.name,
            message
        ])

        # 3. 执行并解析 NDJSON
        result = await run_cli_command(command=cmd, args=args, timeout=300.0)

        async for event in parse_ndjson_stream(result["stdout"]):
            if event.get("type") == "assistant":
                # 提取文本内容
                yield text
    finally:
        # 4. 清理临时文件
        os.unlink(temp_file.name)
```

**为什么用临时文件？**

一开始尝试直接用 stdin 传 system prompt，但：
- CLI 参数有长度限制
- 多行文本转义复杂
- 临时文件更可靠

虽然听起来有点"笨"，但实践证明这是最稳定的方案。

## 技术亮点

### ADR-001: CatConfigLoader 单例模式

```python
class CatConfigLoader:
    _instance: Optional["CatConfigLoader"] = None
    _config: Optional[Dict[str, Any]] = None

    def __new__(cls, config_path: str = "config/cat-config.json"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_path = config_path
        return cls._instance
```

**为什么用单例？**

1. **性能**：配置文件只加载一次，避免重复 I/O
2. **一致性**：全局唯一的配置视图
3. **内存**：避免存储多份配置

**测试技巧**：

单例模式最大的坑是测试——如果不清除，测试之间会互相影响：

```python
@classmethod
def reset(cls):
    """Reset singleton instance (for testing)"""
    cls._instance = None
    cls._config = None
```

每个测试用例前调用 `CatConfigLoader.reset()`，保证隔离性。

### ADR-002: 服务实例缓存

```python
class AgentRouter:
    def __init__(self, config_path: str = "config/cat-config.json"):
        self._services: Dict[str, Any] = {}  # breed_id -> service instance

    def get_service(self, breed_id: str):
        if breed_id not in self._services:
            # 首次访问时创建
            service_class = self._get_service_class(breed_id)
            self._services[breed_id] = service_class(breed_config)

        return self._services[breed_id]
```

**懒加载 + 缓存**：

- **懒加载**：只有在真正需要时才创建服务实例
- **缓存**：创建后保存在 `_services` 字典中
- **好处**：避免一次性初始化所有服务，节省资源

这个模式在后续支持更多猫猫时特别有用——可能有 10+ 只猫，但大部分对话只需要 1-2 只。

## 踩坑记录

### 坑1: tempfile 的 delete=False

一开始用了 `delete=True`（默认值），结果在 Windows 上报错：

```
PermissionError: [WinError 32] The process cannot access the file
```

**原因**：`delete=True` 会在文件关闭时自动删除，但 CLI 进程可能还在读取。

**解决**：用 `delete=False`，手动在 `finally` 块中清理。

```python
temp_file = tempfile.NamedTemporaryFile(
    mode='w', suffix='.txt', delete=False, encoding='utf-8'
)
# ...
finally:
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)
```

### 坑2: NDJSON 解析的边界情况

测试时发现有些 CLI 输出不是标准 NDJSON：

```
{"type": "system", "message": "Starting..."}
{"type": "assistant", "message": {...}}Extra text here
```

**问题**：第二行 JSON 后面有额外文本，导致 `json.loads()` 失败。

**解决**：增强 `parse_ndjson_stream` 的容错性：

```python
async for event in parse_ndjson_stream(result["stdout"]):
    try:
        data = json.loads(line)
        yield data
    except json.JSONDecodeError:
        # 忽略无效行，继续处理
        continue
```

虽然"Extra text"不应该出现，但容错总比崩溃好。

### 坑3: CatConfigLoader 的单例陷阱

写测试时遇到一个奇怪的 bug：

```python
def test_breed_a():
    loader = CatConfigLoader("config-a.json")
    assert loader.get_breed("orange")["name"] == "阿橘"

def test_breed_b():
    loader = CatConfigLoader("config-b.json")  # 想加载不同配置
    # 但实际还是用了 config-a！
```

**原因**：单例在第一次创建后就固定了，后续传入的 `config_path` 被忽略。

**解决**：在每个测试前重置单例：

```python
@pytest.fixture(autouse=True)
def reset_singleton():
    CatConfigLoader.reset()
    yield
    CatConfigLoader.reset()
```

这个教训是：**单例模式要慎用，测试时必须有重置机制**。

## 测试覆盖

### 统计数据

- **测试文件**: 13 个
- **测试用例**: 40 个
- **测试通过率**: 100%

### 关键测试

#### 1. 配置加载测试

```python
def test_load_real_config():
    loader = CatConfigLoader(config_path="config/cat-config.json")
    breeds = loader.list_breeds()

    assert len(breeds) == 3
    assert breeds[0]["id"] == "orange"
    assert breeds[1]["id"] == "inky"
    assert breeds[2]["id"] == "patch"
```

#### 2. 路由测试

```python
def test_route_to_all_three_cats():
    router = AgentRouter(config_path="config/cat-config.json")

    # Test @dev -> orange
    results = router.route_message("@dev help")
    assert results[0]["breed_id"] == "orange"

    # Test @review -> inky
    results = router.route_message("@review this code")
    assert results[0]["breed_id"] == "inky"

    # Test @research -> patch
    results = router.route_message("@research this topic")
    assert results[0]["breed_id"] == "patch"
```

#### 3. 多猫协作测试

```python
def test_multi_cat_mention():
    router = AgentRouter(config_path="config/cat-config.json")

    results = router.route_message("@dev and @review please help")

    assert len(results) == 2
    breed_ids = {r["breed_id"] for r in results}
    assert "orange" in breed_ids
    assert "inky" in breed_ids
```

### 测试金字塔

- **单元测试**: 30 个（配置、路由、工具函数）
- **集成测试**: 10 个（服务调用、CLI 集成）

单元测试占比 75%，符合测试金字塔原则。

## 下一步：Phase 3 预告

明天要实现的功能：

### 1. 流式输出渲染

目前虽然有 `chat_stream()` 方法，但 CLI 还没有实时渲染。

**目标**：
```
阿橘: 这个我熟！<字符逐个出现>
包在我身上！
```

**技术方案**：
- 使用 `rich` 库的 Live Display
- 处理 ANSI 颜色和格式
- 支持中断和错误处理

### 2. 对话历史管理

目前每次对话都是独立的，需要实现：
- Thread 持久化
- 历史加载
- 上下文窗口管理

**挑战**：
- Token 限制（Claude 有 200K 上下文限制）
- 如何截断历史（保留最近 N 条？智能摘要？）

### 3. 多轮对话流程

实现完整的对话循环：
```
用户: @dev 帮我写个函数
阿橘: [响应]
用户: @review 检查一下
墨点: [响应]
```

**关键**：
- 保持对话上下文
- 正确传递历史记录
- 支持切换猫猫

## 个人感悟

今天最大的收获是**架构的重要性**。

一开始如果直接写"三只猫协作"，可能会写出大量 if-else：

```python
# 不要这样做！
if mention == "@dev":
    return OrangeService()
elif mention == "@review":
    return InkyService()
elif mention == "@research":
    return PatchService()
```

但通过 **配置驱动 + 路由映射**，代码变得优雅且可扩展：

```python
# 这样做才对
breed_id = ROLE_TO_BREED.get(mention_text)
if breed_id:
    return self.get_service(breed_id)
```

**核心思想**：
1. **数据驱动**：配置 > 硬编码
2. **单一职责**：路由器只负责路由，不关心具体服务
3. **开闭原则**：添加新猫猫只需修改配置，不需要改代码

另一个感悟是**测试的价值**。

写 `CatConfigLoader` 时，单例模式看起来很完美。但写测试时立刻发现问题——单例无法重置，测试之间互相影响。

**教训**：**如果代码难以测试，说明设计有问题**。

测试不仅是验证功能，更是设计的反馈机制。现在我已经养成了"先写测试，再写实现"的习惯（虽然还不是严格的 TDD，但已经接近了）。

最后，今天学会了**接受"不完美"的方案**。

用临时文件传递 system prompt 看起来很"笨"，但它：
- 可靠（不依赖复杂的参数转义）
- 跨平台（Windows/Linux 都能工作）
- 易于调试（可以直接查看临时文件内容）

**工程不是追求完美，而是追求"足够好"**。过度设计比简单方案更危险。

---

**今日代码行数**: ~800 行（不含测试）
**测试覆盖**: 40 个测试用例
**耗时**: 4 小时
**心情**: 😺😺😺 超级充实！

**关键突破**: 三猫协作框架完成，真实的 CLI 调用跑通！
