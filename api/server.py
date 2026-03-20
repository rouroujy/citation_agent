'''
api/server.py

uvicorn api.server:app --reload --port 8000

访问 http://localhost:8000/docs
'''
from fastapi import FastAPI, UploadFile, File
import shutil
import os

from agent.agent_graph import build_graph
from tools.parse_pdf_tool import parse_pdf
from tools.cache_tool import generate_key, get_cache, set_cache

app = FastAPI()

# 全局只初始化一次
graph = build_graph()

@app.post("/verify_paper")
async def verify(file: UploadFile = File(...)):
    try:
        # 读取文件
        file_bytes = await file.read()
        # 生成key
        key = generate_key(file_bytes)
        # 查缓存
        cached = get_cache(key)
        if cached :
            print("缓存命中")
            return{
                "filename": file.filename,
                "results": cached,
                "cache": True
            }
        
        print("缓存未命中")

        # 保存文件
        save_dir = "data/uploads"
        print("开始处理文件")
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, file.filename)

        with open(file_path, "wb") as f:
            # shutil.copyfileobj(file.file, buffer)
            f.write(file_bytes)

        # 解析PDF
        text = parse_pdf(file_path)
        print("解析PDF完成")

        # 调用agent
        state = {
            "text": text
        }

        result = graph.invoke(state)

        # 写缓存
        results = result.get("result",[])
        set_cache(key, results)

        # 返回结果
        return{
            "filename": file.filename,
            "results":result.get("result",[]),
            "cache": False
        }
    except Exception as e:
        return{
            "error":str(e)
        }