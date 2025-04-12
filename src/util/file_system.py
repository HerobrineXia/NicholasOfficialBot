import os
import urllib.request
import uuid
from datetime import datetime
import urllib
from nonebot import logger
import base64

def read_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            file_content = file.read()
        return file_content
    except FileNotFoundError:
        print("文件未找到！")
        return None
    except IOError:
        print("读取文件时出错！")
        return None
    
def read_file_as_base64(file_path):
    try:
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print("文件未找到！")
        return None
    except IOError:
        print("读取文件时出错！")
        return None

def save_file(url, storage_dir='files') -> str:
    # 拼接文件夹路径
    storage_path = os.path.join('../', storage_dir)
    # 如果文件夹不存在，则创建
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)
    
    # 使用当前时间和 UUID 生成唯一文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    file_name = f"{timestamp}_{unique_id}.jpg"  # 假设文件是 JPG 格式
    
    # 文件的完整路径
    file_path = os.path.join(storage_path, file_name)
    
    # 从url下载文件
    try:
        file = urllib.request.urlopen(url)
        with open(file_path, 'wb') as output:
            output.write(file.read())
            logger.info("Write file at: " + file_path)
        output.close()
    except Exception as e:
        logger.error(f"下载文件时出错：{e}")
        return ""
    return file_path

def remove_file(file_path):
    try:
        os.remove(file_path)
        logger.info("Remove file at: " + file_path)
    except FileNotFoundError:
        logger.error("文件未找到！")
    except IOError:
        logger.error("删除文件时出错！")