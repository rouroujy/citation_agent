import os
from dashscope import Generation
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY")

def call_llm(prompt: str):
    print("\n===============")
    print("\n开始调用百炼")
    response = Generation.call(
        model = "qwen-plus",
        prompt = prompt,
        api_key = api_key
    )
    if response.status_code != 200:
        print("百炼 LLM 调用失败")

    # return response.output.text
    return response.output["text"]