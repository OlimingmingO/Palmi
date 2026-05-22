"""Configurator service — elder profile initialization and understanding doc generation.

Responsibilities:
- Use the project LLM client to convert configurator-supplied free text about an
  elder into a structured Markdown "understanding document".
- Generate a short confirmation summary for the configurator to review.

Errors are handled gracefully: on LLM failure we fall back to returning the raw
text wrapped in a minimal Markdown skeleton so the frontend flow never breaks.
"""
from __future__ import annotations

import logging

from app.utils.llm import chat_completion

logger = logging.getLogger(__name__)


UNDERSTANDING_DOC_PROMPT_TEMPLATE = """你是一位AI助手，负责将配置者提供的关于老人的自由文本描述整理为结构化的"理解文档"。

请将以下文本整理为Markdown格式的理解文档，包含以下章节（如果信息中包含相关内容）：
- # 关于[老人称呼]
- ## 基本信息（姓名、年龄、居住地等）
- ## 日常生活（习惯、爱好、日常活动）
- ## 家人与社交（家庭成员、朋友、社交圈）
- ## 健康状况（已知的健康信息）
- ## 性格特点（性格、偏好）
- ## 敏感区域（需要避免的话题或事项）
- ## [待通过对话补充]

如果某些章节在原文中没有提到相关信息，可以省略该章节。保留原文的语气和用词风格，不要过度润色。

贡献者身份：{contributor_relationship}

原文：
{raw_text}
"""


SUMMARY_PROMPT_TEMPLATE = """你是一位AI助手。请基于以下"理解文档"为配置者生成一段简短的确认摘要。

要求：
- 2-3 句话，控制在 80 字以内
- 抓住老人最核心的画像信息（称呼/年龄/居住地、典型的日常、关键健康信息或性格亮点）
- 以"我了解到："开头
- 不要使用 Markdown 语法，仅输出纯文本

理解文档：
{understanding_doc}
"""


def _fallback_understanding_doc(raw_text: str) -> str:
    """Build a minimal Markdown skeleton from the raw text when the LLM is unavailable."""
    return (
        "# 关于这位老人\n\n"
        "## 基本信息\n\n"
        "（LLM 服务暂不可用，以下为配置者原始描述，未做结构化整理）\n\n"
        f"{raw_text.strip()}\n\n"
        "## [待通过对话补充]\n"
    )


def _fallback_summary(understanding_doc: str) -> str:
    """Best-effort summary if the LLM call fails: take the first non-heading lines."""
    snippet_lines: list[str] = []
    for line in understanding_doc.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        snippet_lines.append(text)
        if len(snippet_lines) >= 2:
            break
    snippet = "；".join(snippet_lines) if snippet_lines else "已记录配置者提供的初始描述"
    return f"我了解到：{snippet}"


async def generate_understanding_doc(raw_text: str, contributor_relationship: str) -> str:
    """Use LLM to parse free-text elder description into structured Markdown.

    Args:
        raw_text: Free-form text from configurator describing the elder.
        contributor_relationship: 子女/社工/邻居/老伴/本人

    Returns:
        Structured Markdown understanding document. Falls back to a minimal
        skeleton wrapping the raw text on LLM failure.
    """
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return "# 关于这位老人\n\n## [待通过对话补充]\n"

    prompt = UNDERSTANDING_DOC_PROMPT_TEMPLATE.format(
        contributor_relationship=contributor_relationship or "未指定",
        raw_text=cleaned,
    )
    messages = [
        {"role": "system", "content": "你是一位帮助家庭整理老人信息的AI助手，输出严格遵守用户指定的Markdown结构。"},
        {"role": "user", "content": prompt},
    ]

    try:
        result = await chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=1500,
        )
        text = (result or "").strip()
        # Strip markdown code fences if the model wrapped the response
        if text.startswith("```"):
            lines = text.split("\n")
            if lines and lines[-1].startswith("```"):
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            text = "\n".join(lines).strip()
        if not text:
            raise ValueError("LLM returned empty understanding doc")
        return text
    except Exception as exc:  # pragma: no cover — fail-soft path
        logger.warning("generate_understanding_doc fell back to raw text: %s", exc)
        return _fallback_understanding_doc(cleaned)


async def generate_summary(understanding_doc: str) -> str:
    """Generate a brief confirmation summary from the understanding doc.

    Returns 2-3 sentences for the configurator to review, e.g.:
    "我了解到：张美兰阿姨，68岁，住上海普陀区。每天去长风公园遛弯..."
    """
    doc = (understanding_doc or "").strip()
    if not doc:
        return "我了解到：暂未录入有效信息。"

    messages = [
        {"role": "system", "content": "你是一位帮助家庭整理老人信息的AI助手，擅长用一两句话概括老人的画像。"},
        {"role": "user", "content": SUMMARY_PROMPT_TEMPLATE.format(understanding_doc=doc)},
    ]

    try:
        result = await chat_completion(
            messages=messages,
            temperature=0.4,
            max_tokens=200,
        )
        summary = (result or "").strip().replace("\n", " ")
        if not summary:
            raise ValueError("LLM returned empty summary")
        return summary
    except Exception as exc:  # pragma: no cover — fail-soft path
        logger.warning("generate_summary fell back to heuristic: %s", exc)
        return _fallback_summary(doc)


async def merge_profile_text(existing_doc: str, new_text: str, contributor_relationship: str) -> str:
    """Merge additional configurator text into an existing understanding doc.

    Strategy: send both the existing doc and the new text to the LLM and ask it
    to produce an updated, merged document that preserves the prior structure.
    Falls back to appending the raw text under a "## [追加描述]" section.
    """
    existing = (existing_doc or "").strip()
    addition = (new_text or "").strip()
    if not addition:
        return existing or "# 关于这位老人\n\n## [待通过对话补充]\n"

    if not existing:
        return await generate_understanding_doc(addition, contributor_relationship)

    merge_prompt = (
        "你是一位AI助手，负责维护老人的'理解文档'。下面给你两份输入：\n"
        "1) 当前的理解文档（Markdown）\n"
        "2) 配置者新提供的补充描述（自由文本）\n\n"
        "请输出更新后的完整理解文档，要求：\n"
        "- 保留原有Markdown章节结构（# / ## 标题）。\n"
        "- 把新描述中的信息合并进合适的章节，不要重复已有内容。\n"
        "- 如果出现新的主题，可以新增对应的 ## 章节。\n"
        "- 保留原文语气，不要过度润色。\n\n"
        f"贡献者身份：{contributor_relationship or '未指定'}\n\n"
        "=== 当前理解文档 ===\n"
        f"{existing}\n\n"
        "=== 新补充描述 ===\n"
        f"{addition}\n"
    )

    messages = [
        {"role": "system", "content": "你是一位帮助家庭维护老人理解文档的AI助手，输出更新后的完整Markdown文档。"},
        {"role": "user", "content": merge_prompt},
    ]

    try:
        result = await chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=2000,
        )
        text = (result or "").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines and lines[-1].startswith("```"):
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            text = "\n".join(lines).strip()
        if not text:
            raise ValueError("LLM returned empty merged doc")
        return text
    except Exception as exc:  # pragma: no cover — fail-soft path
        logger.warning("merge_profile_text fell back to append: %s", exc)
        return f"{existing}\n\n## [追加描述]\n\n{addition}\n"
