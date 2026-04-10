from pathlib import Path
from typing import Dict, List

import yaml

from src.workflow.dag import DAGNode, DAGEdge, QualityGate, WorkflowDAG

_AUTO_PLAN_PROMPT = """你是一个任务规划器。分析以下任务，将其分解为由不同角色猫执行的子任务。

可用的猫和角色：
{cat_list}

任务：{input}

请输出严格的 JSON 格式（不要包含其他文字）：
{{
  "nodes": [
    {{"id": "step_1", "cat_id": "<猫ID>", "prompt": "<该猫的具体任务>"}},
    {{"id": "step_2", "cat_id": "<猫ID>", "prompt": "<该猫的具体任务>"}}
  ],
  "edges": [
    {{"from": "step_1", "to": "step_2"}}
  ]
}}

注意：
- 每个节点的 cat_id 必须是上面列出的猫ID之一
- edges 定义执行依赖和顺序
- 可以有并行节点（无依赖关系）
- 最后一个节点通常是汇总/整合节点"""


class WorkflowTemplateFactory:
    @staticmethod
    def create(template_name: str, cats: List[Dict], message: str) -> WorkflowDAG:
        if not cats:
            raise ValueError("At least one cat is required")
        if template_name == "brainstorm":
            return WorkflowTemplateFactory._brainstorm(cats, message)
        elif template_name == "parallel":
            return WorkflowTemplateFactory._parallel(cats, message)
        elif template_name == "auto_plan":
            return WorkflowTemplateFactory._auto_plan(cats, message)
        elif template_name == "tdd":
            return WorkflowTemplateFactory._tdd(cats, message)
        elif template_name == "review":
            return WorkflowTemplateFactory._review(cats, message)
        elif template_name == "deploy":
            return WorkflowTemplateFactory._deploy(cats, message)
        else:
            raise ValueError(f"Unknown template: {template_name}")

    @staticmethod
    def from_yaml(path: str) -> WorkflowDAG:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        nodes = []
        for nd in data.get("nodes", []):
            nodes.append(DAGNode(
                id=nd["id"], cat_id=nd["cat_id"],
                prompt_template=nd.get("prompt_template", "{input}"),
                role=nd.get("role", ""),
                is_aggregator=nd.get("is_aggregator", False),
            ))
        edges = []
        for ed in data.get("edges", []):
            edges.append(DAGEdge(from_node=ed["from"], to_node=ed["to"]))
        return WorkflowDAG(nodes=nodes, edges=edges)

    @staticmethod
    def _brainstorm(cats: List[Dict], message: str) -> WorkflowDAG:
        nodes = []
        edges = []
        for i, cat in enumerate(cats):
            nodes.append(DAGNode(
                id=f"think_{cat['breed_id']}_{i}",
                cat_id=cat["breed_id"],
                prompt_template="请独立思考并给出你对以下问题的见解：\n\n{input}",
                role=cat["name"],
            ))
        agg_cat = cats[-1]
        nodes.append(DAGNode(
            id="aggregate", cat_id=agg_cat["breed_id"],
            prompt_template="以下是多位专家的独立见解：\n\n{prev_results}\n\n请综合以上观点，给出一个全面、结构化的总结和建议。",
            role=f"{agg_cat['name']}（汇总者）", is_aggregator=True,
        ))
        for n in nodes[:-1]:
            edges.append(DAGEdge(from_node=n.id, to_node="aggregate"))
        return WorkflowDAG(nodes=nodes, edges=edges)

    @staticmethod
    def _parallel(cats: List[Dict], message: str) -> WorkflowDAG:
        nodes = []
        edges = []
        parts = ["前端", "后端", "测试"]
        for i, cat in enumerate(cats):
            part_name = parts[i] if i < len(parts) else f"部分{i + 1}"
            nodes.append(DAGNode(
                id=f"work_{cat['breed_id']}_{i}",
                cat_id=cat["breed_id"],
                prompt_template=f"你是负责**{part_name}**的专家。请针对以下任务，专注于{part_name}部分的工作：\n\n{message}",
                role=f"{cat['name']}（{part_name}）",
            ))
        merge_cat = cats[-1]
        nodes.append(DAGNode(
            id="merge", cat_id=merge_cat["breed_id"],
            prompt_template="以下是团队成员各自完成的部分：\n\n{prev_results}\n\n请将以上各部分整合为一个完整、一致的交付物。确保各部分之间的衔接和一致性。",
            role=f"{merge_cat['name']}（整合者）", is_aggregator=True,
        ))
        for n in nodes[:-1]:
            edges.append(DAGEdge(from_node=n.id, to_node="merge"))
        return WorkflowDAG(nodes=nodes, edges=edges)

    @staticmethod
    def _auto_plan(cats: List[Dict], message: str) -> WorkflowDAG:
        cat_list = "\n".join(f"- {c['breed_id']}: {c['name']}" for c in cats)
        prompt = _AUTO_PLAN_PROMPT.format(cat_list=cat_list, input=message)
        return WorkflowDAG(
            nodes=[DAGNode(id="planner", cat_id=cats[0]["breed_id"], prompt_template=prompt, role="任务规划器")],
            edges=[],
        )

    # === Phase 8.2: SOP Templates ===

    @staticmethod
    def _tdd(cats: List[Dict], message: str) -> WorkflowDAG:
        """SOP: TDD 开发流程 (写测试 → 实现 → 重构)"""
        cat1 = cats[0]
        cat2 = cats[min(1, len(cats) - 1)]
        cat3 = cats[min(2, len(cats) - 1)]

        nodes = [
            DAGNode(
                id="write_tests",
                cat_id=cat1["breed_id"],
                prompt_template=(
                    "你是测试工程师。请根据以下需求编写完整的测试用例：\n\n{input}\n\n"
                    "要求：\n- 每个测试函数以 test_ 开头\n"
                    "- 覆盖正常路径和边界情况\n"
                    "- 使用 assert 语句"
                ),
                role=f"{cat1['name']}（测试工程师）",
            ),
            DAGNode(
                id="implement",
                cat_id=cat2["breed_id"],
                prompt_template=(
                    "你是开发工程师。以下是测试用例：\n\n{prev_results}\n\n"
                    "请编写最小实现让所有测试通过。不要过度设计。"
                ),
                role=f"{cat2['name']}（开发工程师）",
                gate=QualityGate(gate_type="test_exists", description="测试文件存在且包含 test_ 函数"),
            ),
            DAGNode(
                id="refactor",
                cat_id=cat3["breed_id"],
                prompt_template=(
                    "你是代码审查工程师。以下是实现代码：\n\n{prev_results}\n\n"
                    "请进行重构优化：\n- 改善代码结构和可读性\n"
                    "- 确保所有测试仍然通过\n- 不要改变外部行为"
                ),
                role=f"{cat3['name']}（重构工程师）",
                gate=QualityGate(gate_type="test_pass", description="前一步测试通过"),
            ),
        ]
        edges = [
            DAGEdge(from_node="write_tests", to_node="implement"),
            DAGEdge(from_node="implement", to_node="refactor"),
        ]
        return WorkflowDAG(nodes=nodes, edges=edges)

    @staticmethod
    def _review(cats: List[Dict], message: str) -> WorkflowDAG:
        """SOP: 代码审查流程 (审查者1 → 审查者2 → 合并检查)"""
        cat1 = cats[0]
        cat2 = cats[min(1, len(cats) - 1)]
        cat3 = cats[min(2, len(cats) - 1)]

        nodes = [
            DAGNode(
                id="reviewer_1",
                cat_id=cat1["breed_id"],
                prompt_template=(
                    "你是安全审查专家。请审查以下代码的安全性和正确性：\n\n{input}\n\n"
                    "审查要点：\n- 注入漏洞（SQL/XSS/命令注入）\n"
                    "- 权限控制缺陷\n- 数据泄露风险\n"
                    "- 如果发现阻断级别问题，明确标注 BLOCKING"
                ),
                role=f"{cat1['name']}（安全审查）",
            ),
            DAGNode(
                id="reviewer_2",
                cat_id=cat2["breed_id"],
                prompt_template=(
                    "你是性能审查专家。以下是安全审查结果：\n\n{prev_results}\n\n"
                    "请继续审查原始代码的性能和可维护性：\n\n{input}\n\n"
                    "审查要点：\n- 性能瓶颈和资源泄漏\n"
                    "- 代码复杂度和可读性\n- 错误处理完整性\n"
                    "- 如果发现高危问题，明确标注 BLOCKING"
                ),
                role=f"{cat2['name']}（性能审查）",
                gate=QualityGate(gate_type="no_blocking", description="无阻断级别安全问题"),
            ),
            DAGNode(
                id="merge_check",
                cat_id=cat3["breed_id"],
                prompt_template=(
                    "你是合并审查员。以下是完整的审查结果：\n\n{prev_results}\n\n"
                    "请汇总所有审查意见，给出最终结论：\n"
                    "- 列出所有发现的问题（按严重程度排序）\n"
                    "- 给出 APPROVE / REQUEST_CHANGES / BLOCK 建议"
                ),
                role=f"{cat3['name']}（合并审查）",
                is_aggregator=True,
            ),
        ]
        edges = [
            DAGEdge(from_node="reviewer_1", to_node="reviewer_2"),
            DAGEdge(from_node="reviewer_2", to_node="merge_check"),
        ]
        return WorkflowDAG(nodes=nodes, edges=edges)

    @staticmethod
    def _deploy(cats: List[Dict], message: str) -> WorkflowDAG:
        """SOP: 部署发布流程 (运行测试 → 构建检查 → 发布说明)"""
        cat1 = cats[0]
        cat2 = cats[min(1, len(cats) - 1)]
        cat3 = cats[min(2, len(cats) - 1)]

        nodes = [
            DAGNode(
                id="run_tests",
                cat_id=cat1["breed_id"],
                prompt_template=(
                    "你是 QA 工程师。请执行以下部署前的测试检查：\n\n{input}\n\n"
                    "要求：\n- 运行所有单元测试和集成测试\n"
                    "- 报告 passed/failed 数量\n- 标记任何失败项"
                ),
                role=f"{cat1['name']}（QA 工程师）",
            ),
            DAGNode(
                id="build_check",
                cat_id=cat2["breed_id"],
                prompt_template=(
                    "你是构建工程师。测试结果如下：\n\n{prev_results}\n\n"
                    "请执行构建检查：\n- 依赖完整性\n- 安全漏洞扫描\n"
                    "- 构建产物验证\n- 标记任何安全告警"
                ),
                role=f"{cat2['name']}（构建工程师）",
                gate=QualityGate(gate_type="test_pass", description="所有测试通过"),
            ),
            DAGNode(
                id="release_notes",
                cat_id=cat3["breed_id"],
                prompt_template=(
                    "你是发布工程师。以下是构建检查结果：\n\n{prev_results}\n\n"
                    "请生成发布说明：\n- 版本号和发布日期\n"
                    "- 变更列表（新功能/修复/破坏性变更）\n- 升级注意事项"
                ),
                role=f"{cat3['name']}（发布工程师）",
                gate=QualityGate(gate_type="no_blocking", description="无安全告警"),
            ),
        ]
        edges = [
            DAGEdge(from_node="run_tests", to_node="build_check"),
            DAGEdge(from_node="build_check", to_node="release_notes"),
        ]
        return WorkflowDAG(nodes=nodes, edges=edges)
