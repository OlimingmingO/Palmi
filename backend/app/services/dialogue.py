"""Dialogue Service — LLM conversation orchestration.

Responsibilities:
- Receive messages from gateway
- Assemble prompt (persona + memory injection + conversation context)
- Call LLM (Qwen-Max primary, DeepSeek-V3 fallback)
- Post-process response (safety filter, length control)
- Trigger async tasks (memory capture, tag classification)
"""
