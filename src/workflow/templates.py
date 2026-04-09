from pathlib import Path
from typing import Dict, List

import yaml

from src.workflow.dag import DAGNode, DAGEdge, WorkflowDAG

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
