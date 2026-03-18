'''
api/server.py
'''
from fastapi import FastAPI, UploadFile
import shutil

app = FastAPI()

@app.post("/verify_paper")
async def verify(file: UploadFile):
    path = f"data/{file.filename}"

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 调用agent
    return {"msg": "processing"}