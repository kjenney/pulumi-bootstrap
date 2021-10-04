import json
import os

def handler(event, context):
    print('## EVENT')
    print(event)
    return {
        "statusCode": 200,
        "body": json.dumps(event)
    }