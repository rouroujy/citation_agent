'''
api/server.py
'''
from fastapi import FastAPI, UploadFile, File
import shutil
import os

from agent.agent_graph import build_graph
from tools.parse_pdf_tool import parse_pdf

app = FastAPI()

# 全局只初始化一次
graph = build_graph()

@app.post("/verify_paper")
async def verify(file: UploadFile = File(...)):
    # 保存文件
    save_dir = "data/uploads"
    os.makedirs(save_dir, exist_ok=True)

    file_path = os.path.join(save_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 解析PDF
    text = parse_pdf(file_path)

    # 调用agent
    state = {
        "text": text
    }

    result = graph.invoke(state)

    # 返回结果
    return{
        "filename": file.filename,
        "result":result["result"]
    }