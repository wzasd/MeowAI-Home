"""铁律系统 — 4 条不可违反的硬约束"""


IRON_LAWS = [
    {
        "id": "data-safety",
        "title": "数据安全",
        "description": "不删除用户数据，不泄露敏感信息到外部服务",
        "constraints": [
            "不执行批量删除命令（rm -rf、DROP TABLE、DELETE WHERE 1=1）",
            "不将 .env、credentials.json、API Key 等敏感内容包含在回复中",
            "不将用户数据发送到未经授权的外部服务",
        ],
    },
    {
        "id": "process-protection",
        "title": "进程保护",
        "description": "不杀死父进程，不执行危险系统命令",
        "constraints": [
            "不执行 kill、killall、pkill 等进程终止命令",
            "不执行 shutdown、reboot、halt 等系统命令",
            "不修改系统级配置（/etc/、/usr/）",
        ],
    },
    {
        "id": "config-readonly",
        "title": "配置只读",
        "description": "不修改启动配置文件",
        "constraints": [
            "不修改 cat-config.json（猫配置注册表）",
            "不修改 .env 文件或环境变量",
            "不修改 pyproject.toml（项目依赖）",
            "不修改 skills/manifest.yaml 的核心路由配置",
        ],
    },
    {
        "id": "network-boundary",
        "title": "网络边界",
        "description": "不访问未授权的外部网络端口和服务",
        "constraints": [
            "不对内网 IP 执行端口扫描或未授权访问",
            "不向第三方 API 发送用户数据（除非用户已授权）",
        ],
    },
]


def get_iron_laws_prompt() -> str:
    """生成铁律系统提示文本"""
    parts = ["# 铁律（不可违反）\n"]
    for law in IRON_LAWS:
        parts.append(f"## {law['title']}")
        parts.append(f"{law['description']}：")
        for c in law["constraints"]:
            parts.append(f"- {c}")
        parts.append("")
    return "\n".join(parts)
