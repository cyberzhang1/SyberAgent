# core/llm_handler.py
import asyncio
import json
from typing import AsyncGenerator

# ① 从独立模块导入，避免循环导入
from .llm_client import async_client
from .config import settings
from agents.basic_tools import available_tools, tools_metadata
from .memory_manager import memory_manager   # ② 仍保留记忆管理器

conversation_history: dict[str, list[dict]] = {}


async def get_chat_response_stream(
    user_message: str, session_id: str
) -> AsyncGenerator[str, None]:
    """
    获取 LLM 的流式聊天响应，已整合工具调用和知识图谱记忆。
    """
    if session_id not in conversation_history:
        conversation_history[session_id] = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant named Jarvis. "
                           "You can use tools to answer questions and you have a long-term memory."
            }
        ]

    messages = conversation_history[session_id]

    # 步骤1：读取记忆
    retrieved_context = await memory_manager.retrieve_context_for_prompt(user_message)
    full_user_message = retrieved_context + user_message
    messages.append({"role": "user", "content": full_user_message})

    max_turns = 5
    assistant_response = ""

    for _ in range(max_turns):
        response = await async_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            tools=tools_metadata,
            tool_choice="auto",
        )
        response_message = response.choices[0].message

        if response_message.tool_calls:
            messages.append(response_message)

            for tool_call in response_message.tool_calls:
                func_name = tool_call.function.name
                func_to_call = available_tools.get(func_name)

                try:
                    func_args = json.loads(tool_call.function.arguments)
                    yield f"\n[Jarvis is using tool: {func_name}({json.dumps(func_args)})]...\n"
                    func_result = func_to_call(**func_args)
                except Exception as e:
                    func_result = f"Error executing tool {func_name}: {e}"

                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": func_name,
                        "content": str(func_result),
                    }
                )
            continue

        # 无工具调用 → 直接流式输出
        stream = await async_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                assistant_response += delta
                yield delta
                await asyncio.sleep(0.01)

        if assistant_response:
            messages.append({"role": "assistant", "content": assistant_response})

            # 步骤2：写入记忆
            await memory_manager.extract_and_store_triplets(
                f"用户说：{user_message}。AI回复：{assistant_response}"
            )
        return

    yield "Max tool call turns reached. Please try rephrasing your request."