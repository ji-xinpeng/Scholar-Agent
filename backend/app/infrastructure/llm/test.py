from openai import OpenAI
import os
from pydantic import BaseModel

client = OpenAI(
    # 从环境变量中获取方舟 API Key
    api_key="2192cc18-ff14-41bd-a711-f4d35a85bc59",
    base_url = "https://ark.cn-beijing.volces.com/api/v3",
)

class Step(BaseModel):
    explanation: str
    output: str
class MathResponse(BaseModel):
    steps: list[Step]
    final_answer: str
    
completion = client.chat.completions.parse(
    model = "doubao-seed-1-6-250615",  # 替换为您需要使用的模型
    messages = [
        {"role": "system", "content": "你是一位数学辅导老师。"},
        {"role": "user", "content": "使用中文解题: 8x + 9 = 32 and x + y = 1"},
    ],
    response_format=MathResponse,
    extra_body={
         "thinking": {
             "type": "disabled" # 不使用深度思考能力
             # "type": "enabled" # 使用深度思考能力
         }
     }
)
resp = completion.choices[0].message.parsed
# 打印 JSON 格式结果
print(resp.model_dump_json(indent=2))