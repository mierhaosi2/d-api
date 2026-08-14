from langchain.agents import create_agent
from dotenv import load_dotenv
load_dotenv()

def get_weather(city:str) -> str:
    """Get the weather of a city"""
    return f"The weather of {city} is sunny"

# create_封装整个agent调用的流程
agent = create_agent(
    model="openrouter:deepseek/deepseek-v4-flash-0731",
    tools=[get_weather],
    system_prompt="You are a weather agent. You are tasked with getting the weather of a city.",
)
result = agent.invoke(
    {"messages":[{"role":"user","content":"What is the weather in Tokyo?"}]}
)
print(result["messages"][-1].content)


