import json
from datetime import datetime, date
from bson import ObjectId
from fastapi import UploadFile
from typing import List

def check_s3_file(s3, bucket_name, key):
    try:
        s3.head_object(Bucket=bucket_name, Key=key)
        return True
    except Exception as e:
        return False

def check_valid_file_type(files: List[UploadFile]):
    valid_types = ["text/plain"]
    
    for file in files:
        if file.content_type not in valid_types:
            print("Invalid file type" + file.content_type)
            return False
    return True

def convert_message_format(message):
    history_data = json.loads(message["History"])
    converted_message = {
        "_id": message["_id"],
        "SessionId": message["SessionId"],
        "type": history_data["type"],
        "content": history_data["data"]["content"]
    }
    return converted_message

#Custom JSON Encoder
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)