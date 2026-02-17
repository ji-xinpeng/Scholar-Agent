"""
使用示例

演示如何使用 LLM 调度服务
"""
import asyncio
from app.domain.llm_scheduler import llm_service, ChatMessage, MessageRole


async def example_basic_chat():
    """基础对话示例"""
    messages = [
        ChatMessage(role=MessageRole.USER, content="你好，请介绍一下自己")
    ]

    response = await llm_service.chat(messages)
    print(f"回复内容: {response.content}")
    print(f"使用模型: {response.model}")
    print(f"Token 使用: {response.usage}")


async def example_stream_chat():
    """流式对话示例"""
    messages = [
        ChatMessage(role=MessageRole.USER, content="请写一首关于春天的诗")
    ]

    print("流式输出:")
    async for chunk in llm_service.chat_stream(messages):
        print(chunk, end="", flush=True)
    print()


async def example_switch_provider():
    """切换提供商示例"""
    messages = [
        ChatMessage(role=MessageRole.USER, content="Hello, what can you do?")
    ]

    print("\n使用 Qwen:")
    response = await llm_service.chat(messages, provider="qwen")
    print(response.content)

    print("\n使用 DeepSeek:")
    response = await llm_service.chat(messages, provider="deepseek")
    print(response.content)


async def example_list_providers():
    """列出所有可用提供商"""
    providers = llm_service.list_available_providers()
    print("\n可用的模型提供商:")
    for p in providers:
        print(f"  - {p['name']}")
        print(f"    默认模型: {p['default_model']}")
        print(f"    支持的模型: {', '.join(p['supported_models'])}")


if __name__ == "__main__":
    asyncio.run(example_basic_chat())
