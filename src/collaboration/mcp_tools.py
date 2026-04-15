"""MCP 工具实现"""
from typing import Any, Dict, List, Optional
import asyncio
import ast
import os
import re

from pathlib import Path
from src.thread.models import Thread


# === 安全防护 ===

# 命令执行黑名单
COMMAND_BLACKLIST = [
    r"\brm\s+-rf\b", r"\bsudo\b", r"\bchmod\s+777\b",
    r"\bcurl\b.*\|\s*sh\b", r"\bwget\b.*\|\s*sh\b",
    r"\bmkfs\b", r"\bdd\b.*of=/dev/", r"\bformat\b",
    # Phase 8.1: 进程保护 + 系统安全
    r"\bkill\s+-9\b", r"\bkillall\b", r"\bpkill\b",
    r"\bshutdown\b", r"\breboot\b", r"\bhalt\b",
]

# 受保护的配置文件（铁律 3: 配置只读）
PROTECTED_PATHS = [
    "cat-config.json",
    ".env",
    "pyproject.toml",
    "skills/manifest.yaml",
]

# 允许的 git 操作白名单
GIT_ALLOWED_ACTIONS = {"status", "diff", "log", "branch", "show", "stash", "remote"}

# 输出最大字节数
MAX_OUTPUT_BYTES = 10240


def _is_command_safe(command: str) -> bool:
    """检查命令是否安全"""
    for pattern in COMMAND_BLACKLIST:
        if re.search(pattern, command, re.IGNORECASE):
            return False
    return True


def _is_path_protected(path: str) -> bool:
    """检查文件路径是否受铁律保护"""
    p = Path(path)
    for protected in PROTECTED_PATHS:
        if p.name == protected or str(p).endswith(protected):
            return True
    return False


def _truncate_output(output: str) -> str:
    """截断输出到最大字节数"""
    encoded = output.encode('utf-8')
    if len(encoded) > MAX_OUTPUT_BYTES:
        return output[:MAX_OUTPUT_BYTES // 2] + "\n... (truncated)"
    return output


# === 文件操作工具 ===

async def read_file_tool(path: str, start_line: int = None, end_line: int = None) -> Dict[str, Any]:
    """读取文件内容（支持行号范围）"""
    file_path = Path(path)
    if not file_path.exists():
        return {"error": f"File not found: {path}"}
    if not file_path.is_file():
        return {"error": f"Not a file: {path}"}

    try:
        lines = file_path.read_text(encoding='utf-8', errors='replace').splitlines()
        total_lines = len(lines)

        if start_line is not None:
            lines = lines[start_line - 1:]
        if end_line is not None:
            lines = lines[:end_line - (start_line or 1) + 1]

        content = "\n".join(f"{i}: {line}" for i, line in enumerate(
            lines, start=start_line or 1
        ))
        return {"content": _truncate_output(content), "lines": total_lines}
    except Exception as e:
        return {"error": str(e)}


async def read_interactive_response_tool(thread_id: str, block_id: str = None) -> Dict[str, Any]:
    """读取用户在 interactive block 中的选择结果"""
    from src.thread import ThreadManager
    manager = ThreadManager()
    thread = await manager.get(thread_id)
    if not thread:
        return {"error": f"Thread not found: {thread_id}"}

    responses = thread.metadata.get("interactive_responses", []) if thread.metadata else []
    if block_id:
        responses = [r for r in responses if r.get("block_id") == block_id]

    return {
        "responses": responses[-10:],  # Return last 10 matching responses
        "total": len(responses),
    }


async def read_uploaded_file_tool(thread_id: str, filename: str) -> Dict[str, Any]:
    """读取用户上传到 thread 的附件内容"""
    from src.thread import ThreadManager
    manager = ThreadManager()
    thread = await manager.get(thread_id)
    if not thread:
        return {"error": f"Thread not found: {thread_id}"}
    if not thread.project_path:
        return {"error": "Thread has no project path"}

    upload_dir = Path(thread.project_path) / ".meowai" / "uploads" / thread_id
    file_path = upload_dir / filename

    # Security check: resolved path must be within upload_dir
    resolved_path = file_path.resolve()
    resolved_dir = upload_dir.resolve()
    if not str(resolved_path).startswith(str(resolved_dir)):
        return {"error": "Path traversal detected"}

    return await read_file_tool(str(file_path))


async def write_file_tool(path: str, content: str, create_dirs: bool = False) -> Dict[str, Any]:
    """写入文件（受保护路径检查）"""
    if _is_path_protected(path):
        return {"error": f"Path is protected by iron laws: {path}"}
    file_path = Path(path)
    try:
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return {"status": "written", "path": str(file_path)}
    except Exception as e:
        return {"error": str(e)}


async def list_files_tool(path: str = ".", pattern: str = "*", recursive: bool = False) -> Dict[str, Any]:
    """列出目录内容"""
    dir_path = Path(path)
    if not dir_path.exists():
        return {"error": f"Directory not found: {path}", "files": [], "total": 0}

    try:
        if recursive:
            items = list(dir_path.rglob(pattern))
        else:
            items = list(dir_path.glob(pattern))

        files = []
        for item in sorted(items)[:100]:
            files.append({
                "name": item.name,
                "path": str(item.relative_to(dir_path)) if recursive else item.name,
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0
            })
        return {"files": files, "total": len(files)}
    except Exception as e:
        return {"error": str(e), "files": [], "total": 0}


async def analyze_code_tool(path: str) -> Dict[str, Any]:
    """分析 Python 代码结构"""
    file_path = Path(path)
    if not file_path.exists():
        return {"error": f"File not found: {path}"}
    if not file_path.suffix == '.py':
        return {"error": f"Not a Python file: {path}"}

    try:
        source = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source)

        functions = [
            {"name": node.name, "line": node.lineno, "args": [a.arg for a in node.args.args]}
            for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        classes = [
            {"name": node.name, "line": node.lineno, "bases": [ast.dump(b) for b in node.bases][:3]}
            for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append({
                    "module": node.module or "",
                    "line": node.lineno,
                    "names": [a.name for a in node.names][:5]
                })
            elif isinstance(node, ast.Import):
                imports.append({
                    "module": "",
                    "line": node.lineno,
                    "names": [a.name for a in node.names][:5]
                })

        return {
            "functions": functions[:20],
            "classes": classes[:10],
            "imports": imports[:15],
            "lines": len(source.splitlines())
        }
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}
    except Exception as e:
        return {"error": str(e)}


# === 命令执行工具 ===

async def execute_command_tool(command: str, cwd: str = ".", timeout: int = 30) -> Dict[str, Any]:
    """执行 shell 命令（安全沙箱）"""
    if not _is_command_safe(command):
        return {"error": "Command blocked by security policy", "stdout": "", "stderr": "", "exit_code": -1}

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "stdout": _truncate_output(stdout.decode('utf-8', errors='replace')),
            "stderr": _truncate_output(stderr.decode('utf-8', errors='replace')),
            "exit_code": proc.returncode
        }
    except asyncio.TimeoutError:
        proc.kill()
        return {"error": f"Command timed out ({timeout}s)", "stdout": "", "stderr": "", "exit_code": -1}
    except Exception as e:
        return {"error": str(e), "stdout": "", "stderr": "", "exit_code": -1}


async def run_tests_tool(test_path: str = None, verbose: bool = False) -> Dict[str, Any]:
    """运行 pytest 测试"""
    cmd = ["python3", "-m", "pytest", "--tb=short", "-q"]
    if test_path:
        cmd.append(test_path)
    if verbose:
        cmd.append("-v")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode('utf-8', errors='replace')

        # 解析 pytest 输出
        passed = failed = 0
        for line in output.splitlines():
            if " passed" in line:
                parts = line.split()
                for p in parts:
                    if "passed" in p:
                        passed = int(p.replace("passed", "").strip())
                    if "failed" in p:
                        failed = int(p.replace("failed", "").strip())

        return {
            "passed": passed,
            "failed": failed,
            "output": _truncate_output(output),
            "exit_code": proc.returncode
        }
    except asyncio.TimeoutError:
        return {"error": "Tests timed out (60s)", "passed": 0, "failed": 0, "output": ""}
    except Exception as e:
        return {"error": str(e), "passed": 0, "failed": 0, "output": ""}


async def git_operation_tool(action: str, args: Dict[str, str] = None) -> Dict[str, Any]:
    """Git 操作（安全白名单）"""
    if action not in GIT_ALLOWED_ACTIONS:
        return {"error": f"Git action not allowed: {action}. Allowed: {GIT_ALLOWED_ACTIONS}"}

    cmd = f"git {action}"
    if args:
        for k, v in args.items():
            cmd += f" --{k}={v}"

    if not _is_command_safe(cmd):
        return {"error": "Command blocked by security policy"}

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        return {
            "result": _truncate_output(stdout.decode('utf-8', errors='replace')),
            "exit_code": proc.returncode
        }
    except asyncio.TimeoutError:
        return {"error": "Git operation timed out"}
    except Exception as e:
        return {"error": str(e)}


# === 记忆查询工具 ===

async def save_memory_tool(key: str, value: str, category: str = "general") -> Dict[str, Any]:
    """保存键值对到项目记忆"""
    from src.collaboration.mcp_memory import MemoryStore
    store = MemoryStore()
    return await store.save(key, value, category)


async def query_memory_tool(key: str = None, category: str = None) -> Dict[str, Any]:
    """查询项目记忆"""
    from src.collaboration.mcp_memory import MemoryStore
    store = MemoryStore()
    return await store.query(key=key, category=category)


async def search_knowledge_tool(query: str, max_results: int = 10) -> Dict[str, Any]:
    """搜索知识库（文件 + 记忆）"""
    from src.collaboration.mcp_memory import MemoryStore
    store = MemoryStore()

    # 搜索记忆
    memory_results = await store.search(query, max_results=max_results)

    # 搜索文件
    file_results = await search_files_tool(query)

    return {
        "memory": memory_results.get("results", []),
        "files": file_results.get("matches", []),
        "total": len(memory_results.get("results", [])) + len(file_results.get("matches", []))
    }


async def search_all_memory_tool(query: str, max_results: int = 10) -> Dict[str, Any]:
    """搜索所有记忆层（对话、知识、经验）"""
    from src.memory import MemoryService
    service = MemoryService()

    results = {
        "episodes": [],
        "entities": [],
        "procedures": [],
    }

    keywords = query.replace("的", " ").split()
    for kw in keywords:
        if len(kw) < 2:
            continue
        episodes = service.episodic.search(kw, limit=max_results)
        entities = service.semantic.search_entities(kw, limit=3)
        procedures = service.procedural.search(kw, limit=3)
        results["episodes"].extend([{"content": e["content"][:100], "importance": e["importance"]} for e in episodes])
        results["entities"].extend([{"name": e["name"], "type": e["type"], "description": e.get("description", "")} for e in entities])
        results["procedures"].extend([{"name": p["name"], "success_rate": p["success_count"] / max(p["success_count"] + p["fail_count"], 1)} for p in procedures])

    # Deduplicate
    for key in results:
        seen = set()
        unique = []
        for item in results[key]:
            ident = str(item)
            if ident not in seen:
                seen.add(ident)
                unique.append(item)
        results[key] = unique[:max_results]

    results["total"] = len(results["episodes"]) + len(results["entities"]) + len(results["procedures"])
    return results


# === 协作增强工具 ===

async def create_thread_tool(thread: Thread, name: str) -> Dict[str, Any]:
    """创建新 Thread"""
    from src.thread import ThreadManager
    manager = ThreadManager()
    new_thread = await manager.create(name)
    return {"thread_id": new_thread.id, "name": new_thread.name}


async def list_threads_tool(keyword: str = None) -> Dict[str, Any]:
    """列出所有 Thread"""
    from src.thread import ThreadManager
    manager = ThreadManager()
    threads = await manager.list()

    result = []
    for t in threads:
        if keyword and keyword.lower() not in t.name.lower():
            continue
        result.append({
            "id": t.id,
            "name": t.name,
            "messages": len(t.messages),
            "created_at": str(t.created_at)
        })

    return {"threads": result, "total": len(result)}


# === 原有工具 ===

async def post_message_tool(thread: Thread, content: str) -> Dict[str, Any]:
    """发送消息到当前 thread"""
    thread.add_message("assistant", content)
    return {
        "status": "sent",
        "message_preview": content[:50] + "..." if len(content) > 50 else content
    }


async def search_files_tool(query: str, path: str = ".") -> Dict[str, Any]:
    """搜索项目文件内容"""
    matches = []
    max_matches = 10

    try:
        base_path = Path(path)

        for pattern in ["*.py", "*.md"]:
            for file_path in base_path.rglob(pattern):
                if len(matches) >= max_matches:
                    break

                try:
                    with file_path.open('r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if query.lower() in line.lower():
                                matches.append({
                                    "file": str(file_path.relative_to(base_path)),
                                    "line": line_num,
                                    "content": line.strip()[:100]
                                })
                                if len(matches) >= max_matches:
                                    break
                except Exception:
                    continue

            if len(matches) >= max_matches:
                break

    except Exception as e:
        return {"matches": [], "error": str(e)}

    return {"matches": matches}


async def target_cats_tool(cats: List[str]) -> Dict[str, Any]:
    """声明下一个回复的猫（结构化路由）"""
    return {"targetCats": cats}


# === 工具注册配置 ===

TOOL_REGISTRY = {
    # 文件操作
    "read_file": {
        "description": "读取文件内容（支持行号范围）",
        "parameters": {
            "path": {"type": "string", "description": "文件路径"},
            "start_line": {"type": "integer", "description": "起始行号（可选）"},
            "end_line": {"type": "integer", "description": "结束行号（可选）"}
        },
        "handler": read_file_tool
    },
    "read_uploaded_file": {
        "description": "读取用户上传到当前 Thread 的附件内容",
        "parameters": {
            "thread_id": {"type": "string", "description": "Thread ID"},
            "filename": {"type": "string", "description": "上传时的文件名"}
        },
        "handler": read_uploaded_file_tool
    },
    "read_interactive_response": {
        "description": "读取用户在 interactive block 中的选择结果",
        "parameters": {
            "thread_id": {"type": "string", "description": "Thread ID"},
            "block_id": {"type": "string", "description": "Interactive block ID（可选）"}
        },
        "handler": read_interactive_response_tool
    },
    "write_file": {
        "description": "写入/创建文件",
        "parameters": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "文件内容"},
            "create_dirs": {"type": "boolean", "description": "自动创建目录（可选）"}
        },
        "handler": write_file_tool
    },
    "list_files": {
        "description": "列出目录内容（支持过滤和递归）",
        "parameters": {
            "path": {"type": "string", "description": "目录路径（默认当前目录）"},
            "pattern": {"type": "string", "description": "glob 匹配模式（默认 *）"},
            "recursive": {"type": "boolean", "description": "是否递归（默认否）"}
        },
        "handler": list_files_tool
    },
    "analyze_code": {
        "description": "分析 Python 代码结构（函数/类/导入）",
        "parameters": {
            "path": {"type": "string", "description": "Python 文件路径"}
        },
        "handler": analyze_code_tool
    },
    # 命令执行
    "execute_command": {
        "description": "执行 shell 命令（安全沙箱，30s 超时）",
        "parameters": {
            "command": {"type": "string", "description": "要执行的命令"},
            "cwd": {"type": "string", "description": "工作目录（默认当前目录）"},
            "timeout": {"type": "integer", "description": "超时秒数（默认 30）"}
        },
        "handler": execute_command_tool
    },
    "run_tests": {
        "description": "运行 pytest 测试",
        "parameters": {
            "test_path": {"type": "string", "description": "测试路径（可选）"},
            "verbose": {"type": "boolean", "description": "详细输出（默认否）"}
        },
        "handler": run_tests_tool
    },
    "git_operation": {
        "description": "Git 操作（status/diff/log/branch/show/stash/remote）",
        "parameters": {
            "action": {"type": "string", "description": "Git 操作名"},
            "args": {"type": "object", "description": "额外参数（可选）"}
        },
        "handler": git_operation_tool
    },
    # 记忆查询
    "save_memory": {
        "description": "保存键值对到项目记忆",
        "parameters": {
            "key": {"type": "string", "description": "记忆键名"},
            "value": {"type": "string", "description": "记忆值"},
            "category": {"type": "string", "description": "分类（默认 general）"}
        },
        "handler": save_memory_tool
    },
    "query_memory": {
        "description": "查询项目记忆",
        "parameters": {
            "key": {"type": "string", "description": "按键查询（可选）"},
            "category": {"type": "string", "description": "按分类查询（可选）"}
        },
        "handler": query_memory_tool
    },
    "search_knowledge": {
        "description": "搜索知识库（文件 + 记忆）",
        "parameters": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {"type": "integer", "description": "最大结果数（默认 10）"}
        },
        "handler": search_knowledge_tool
    },
    "search_all_memory": {
        "description": "搜索所有记忆层（对话、知识、经验），返回最相关的记忆",
        "parameters": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {"type": "integer", "description": "每层最大结果数（默认 10）"}
        },
        "handler": search_all_memory_tool
    },
    # 协作增强
    "create_thread": {
        "description": "创建新 Thread",
        "parameters": {
            "name": {"type": "string", "description": "Thread 名称"}
        },
        "handler": create_thread_tool
    },
    "list_threads": {
        "description": "列出所有 Thread（支持关键词过滤）",
        "parameters": {
            "keyword": {"type": "string", "description": "过滤关键词（可选）"}
        },
        "handler": list_threads_tool
    },
    # 原有工具
    "post_message": {
        "description": "发送消息到当前 thread",
        "parameters": {
            "content": {"type": "string", "description": "消息内容"}
        },
        "handler": post_message_tool
    },
    "search_files": {
        "description": "搜索项目文件内容",
        "parameters": {
            "query": {"type": "string", "description": "搜索关键词"},
            "path": {"type": "string", "description": "搜索路径（默认当前目录）"}
        },
        "handler": search_files_tool
    },
    "targetCats": {
        "description": "声明下一个回复的猫",
        "parameters": {
            "cats": {
                "type": "array",
                "description": "猫 ID 列表",
                "items": {"type": "string"}
            }
        },
        "handler": target_cats_tool
    }
}
