"""Scope Guard — detect conversation drift"""
from dataclasses import dataclass
from collections import Counter
import re
from typing import List

from src.memory import EpisodicMemory


@dataclass
class DriftResult:
    is_drift: bool
    similarity: float
    thread_topic: str
    warning: str
    confidence: float


def _tokenize(text: str) -> List[str]:
    """Tokenize: split English on word boundaries, CJK into bigrams."""
    tokens = []
    # Extract English words (>= 2 chars)
    for word in re.findall(r'[a-zA-Z]{2,}', text):
        tokens.append(word.lower())
    # Extract CJK bigrams (characters in CJK Unicode ranges)
    cjk_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text)
    for i in range(len(cjk_chars) - 1):
        tokens.append(cjk_chars[i] + cjk_chars[i + 1])
    # Also include single CJK chars for short text
    for ch in cjk_chars:
        tokens.append(ch)
    return tokens


class ScopeGuard:
    def __init__(self, episodic_memory: EpisodicMemory, threshold: float = 0.3):
        self.episodic = episodic_memory
        self.threshold = threshold

    def check_drift(
        self,
        current_message: str,
        thread_id: str,
        recent_window: int = 5,
    ) -> DriftResult:
        episodes = self.episodic.recall_by_thread(thread_id, limit=recent_window)
        if not episodes:
            return DriftResult(False, 1.0, "", "", 1.0)

        current_tokens = set(_tokenize(current_message))
        if len(current_tokens) < 2:
            return DriftResult(False, 1.0, "", "", 1.0)

        # Build topic bag from thread history
        topic_bag = Counter()
        for ep in episodes:
            for token in _tokenize(ep.get("content", "")):
                topic_bag[token] += 1

        if not topic_bag:
            return DriftResult(False, 1.0, "", "", 1.0)

        # Jaccard similarity
        topic_keys = set(topic_bag.keys())
        intersection = current_tokens & topic_keys
        union = current_tokens | topic_keys
        similarity = len(intersection) / len(union) if union else 0.0

        # Extract top topic keywords
        top_keywords = [word for word, _ in topic_bag.most_common(3)]
        thread_topic = " ".join(top_keywords)

        is_drift = similarity < self.threshold
        confidence = 1.0 - abs(similarity - self.threshold) / max(self.threshold, 0.01)

        return DriftResult(
            is_drift=is_drift,
            similarity=similarity,
            thread_topic=thread_topic,
            warning="",
            confidence=min(max(confidence, 0.0), 1.0),
        )

    def build_drift_warning(self, drift_result: DriftResult) -> str:
        if not drift_result.is_drift:
            return ""
        return (
            f"## 话题偏移提醒\n"
            f"当前对话主题似乎偏离了原有话题「{drift_result.thread_topic}」。"
            f"如果是有意的，请忽略此提醒。"
        )
