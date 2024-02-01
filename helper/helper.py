import json
def convert_message_format(message):
    history_data = json.loads(message["History"])
    converted_message = {
        "_id": message["_id"],
        "SessionId": message["SessionId"],
        "type": history_data["type"],
        "content": history_data["data"]["content"]
    }
    return converted_message