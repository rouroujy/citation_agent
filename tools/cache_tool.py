'''
tools/cache_tool.py

sudo apt update
sudo apt install redis-server -y
sudo service redis-server start

redis-cli ping
'''

import redis
import hashlib
import json

# WSL本地连接
r = redis.Redis(host = "localhost", port = 6379, db = 0)

def generate_key(file_bytes: bytes):
    return hashlib.md5(file_bytes).hexdigest()

def get_cache(key):
    try:
        data = r.get(key)
        if data:
            return json.loads(data)
        
    except Exception as e:
        print("读取redis失败：",e)

    return None

def set_cache(key, value, expire = 3600):
    try:
        r.set(key,json.dumps(value), ex = expire)
    
    except Exception as e:
        print("写入redis失败：", e)