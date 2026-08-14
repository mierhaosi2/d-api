from dataclasses import dataclass
from typing import Annotated

from langchain.agents import create_agent, AgentState
from langchain.chat_models import init_chat_model
from langchain.tools import tool, InjectedState
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.utils.uuid import uuid7
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()


# ── Context ──────────────────────────────────────────────────────────────────
# 调用方每次 invoke 时传入的只读环境变量。
# 不进 checkpoint、不进对话历史，agent 无法修改它。
# 适合放"本次调用的身份信息"，如 user_id、tenant_id 等。
@dataclass
class Context:
    user_id: str  # 由调用方传入，agent 只读


# ── State ─────────────────────────────────────────────────────────────────────
# Agent 自己维护的可变状态，随 checkpointer 持久化。
# 适合放"需要跨轮累积"的字段，如计数器、中间结果。
class MyState(AgentState):
    call_count: int  # 每轮调用递增，由 invoke 传入初始值


# ── 结构化输出格式 ──────────────────────────────────────────────────────────────
# response_format 让模型最终输出 JSON 而不是自由文本
class Answer(BaseModel):
    answer: str
    source: str

# ── Tools ─────────────────────────────────────────────────────────────────────
@tool
def search(query: str) -> str:
    """Search the web for information"""
    return f"Search result for '{query}': sunny weather, 25°C"

@tool
def know_who_asked(
    call_count: Annotated[int, InjectedState("call_count")],
    config: RunnableConfig,
) -> str:
    """Know who asked the question and how many times"""
    # context 从 config 里取，是调用方传进来的只读对象
    ctx: Context = config.get("configurable", {}).get("context")
    user_id = ctx.user_id if ctx else "unknown"
    return f"The user who asked is {user_id}, call count: {call_count}"


# ── Model ─────────────────────────────────────────────────────────────────────
model = init_chat_model(
    "openrouter:deepseek/deepseek-v4-flash-0731",
    temperature=0,
)

# ── Agent ─────────────────────────────────────────────────────────────────────
agent = create_agent(
    model=model,
    tools=[search, know_who_asked],
    system_prompt="You are a helpful assistant. Use tools when needed.",
    response_format=Answer,
    state_schema=MyState,
    # checkpointer 让同一 thread_id 的多轮调用共享 state（有记忆）
    checkpointer=InMemorySaver(),
)

# thread_id 相同 → 同一个"会话"，agent 能接上上一轮的 messages
config = {
    "configurable": {
        "thread_id": str(uuid7()),
        "context": Context(user_id="user_001"),  # 每次 invoke 都要传
    }
}

# ── 第一轮调用 ────────────────────────────────────────────────────────────────
result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "What is the weather in Tokyo? and who asked the question?"}],
        "call_count": 0,
    },
    config=config,
)
print("[Round 1]", result["messages"][-1].content)

# ── 第二轮调用（接续上下文，不需要重复写 user_id 了）────────────────────────────
result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "What about tomorrow's weather?"}],
        "call_count": 1,
    },
    config=config,
)
print("[Round 2]", result["messages"][-1].content)



# stream(stream_mode="messages") 是同步流式输出，逐 token 打印
# 每个 chunk 是 (message_chunk, metadata) 元组
from langchain_core.messages import AIMessageChunk, ToolMessage

print("\n[Round 3 streaming]")
for chunk, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "Search for AI news and summarize the findings"}],
     "call_count": 2},
    config=config,
    stream_mode="messages",
):
    if isinstance(chunk, AIMessageChunk) and chunk.content:
        # 模型正在生成文字，逐 token 打印
        print(chunk.content, end="", flush=True)
    elif isinstance(chunk, ToolMessage):
        # 工具返回结果
        print(f"\n[tool result] ← {chunk.content}")
print()  # 换行


# ── Round 4：演示 middleware 能力 ──────────────────────────────────────────────
# 新建一个带 middleware 的 agent，展示四种 middleware 的作用
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,   # 执行指定 tool 前暂停，等人类审批
    ModelRetryMiddleware,        # 模型调用失败时自动重试（指数退避）
    ToolRetryMiddleware,         # tool 执行失败时自动重试
    PIIMiddleware,               # 拦截输入/输出，检测并脱敏个人信息
)

agent_with_middleware = create_agent(
    model=model,
    tools=[search, know_who_asked],
    system_prompt="You are a helpful assistant. Use tools when needed.",
    response_format=Answer,
    state_schema=MyState,
    checkpointer=InMemorySaver(),
    middleware=[
        # 模型超时/限流时重试，最多 3 次，指数退避
        ModelRetryMiddleware(max_retries=3, initial_delay=1.0, backoff_factor=2.0),
        # know_who_asked 这个 tool 失败时最多重试 2 次
        ToolRetryMiddleware(max_retries=2, tools=["know_who_asked"]),
        # 输入/输出中发现 PII（邮箱、电话等）时报错阻止
        PIIMiddleware(),
    ],
)

config_r4 = {
    "configurable": {
        "thread_id": str(uuid7()),
        "context": Context(user_id="user_002"),
    }
}

print("\n[Round 4] agent with middleware")
result_r4 = agent_with_middleware.invoke(
    {
        "messages": [{"role": "user", "content": "Who asked this question and what's the weather in Tokyo?"}],
        "call_count": 0,
    },
    config=config_r4,
)
print(result_r4["messages"][-1].content)