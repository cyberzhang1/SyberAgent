# agents/basic_tools.py

import datetime
import json

def get_current_time() -> str:
    """
    获取当前日期和时间。
    :return: 格式为 'YYYY-MM-DD HH:MM:SS' 的当前时间字符串。
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_weather(location: str) -> str:
    """
    获取指定地点的天气信息（这是一个模拟函数）。
    :param location: 城市名称，例如 "北京"。
    :return: 一个描述天气的JSON字符串。
    """
    # 在真实应用中，这里会调用一个真实的天气API
    if "北京" in location:
        return json.dumps({"location": "北京", "temperature": "25°C", "condition": "晴"})
    elif "上海" in location:
        return json.dumps({"location": "上海", "temperature": "28°C", "condition": "多云"})
    else:
        return json.dumps({"location": location, "error": "未知地点"})

# --- 工具注册表 ---
# 将函数本身映射到一个名称
available_tools = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
}

# --- 工具元数据 ---
# 这是提供给LLM的“工具说明书”，格式需遵循LLM的要求
tools_metadata = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期和时间。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取一个指定地点的天气信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市和省份，例如：北京",
                    }
                },
                "required": ["location"],
            },
        },
    },
]