from app.memory.schemas import PlanningContext


def assemble_planning_context(
    *,
    instruction: str,
    task_summary: str | None,
    conversation_lines: list[str],
    tool_result_lines: list[str],
    user_preferences: dict[str, str],
    checkpoint_note: str | None,
    max_chars: int,
) -> tuple[PlanningContext, bool]:
    truncated = False
    conv = list(conversation_lines)
    tools = list(tool_result_lines)

    def _total() -> int:
        parts = [instruction, task_summary or "", checkpoint_note or ""]
        parts.extend(conv)
        parts.extend(tools)
        parts.extend(f"{k}={v}" for k, v in user_preferences.items())
        return sum(len(part) for part in parts if part)

    while _total() > max_chars and (conv or tools):
        truncated = True
        if len(conv) >= len(tools) and conv:
            conv.pop(0)
        elif tools:
            tools.pop(0)
        else:
            break

    return (
        PlanningContext(
            task_instruction=instruction,
            task_summary=task_summary,
            conversation_turns=conv,
            recent_tool_results=tools,
            user_preferences=user_preferences,
            checkpoint_note=checkpoint_note,
        ),
        truncated,
    )