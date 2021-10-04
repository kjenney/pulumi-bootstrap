import json
import os

def handler(event, context):
    print('## BODY')
    #print(event)
    #for k in event:
    #    print(k)
    #print(event.keys())
    #print(event['version'])
    print(event['body'])
    #print(event['body'][0]['action'])
    # If the Pull Request is not closed - let's do something
    # if event['body']['pull_request']['closed_at'] != 'null':
    #     # If the Pull Request is merged Zip up the source to S3 via CodeBuild else Lint the code
    #     if event['body']['pull_request']['merged_at'] != 'null':
    #         print('Kick off CodeBuild S3 Copy')
    #     else:
    #         print('Kick off CodeBuild Lint')
    return {
        "statusCode": 200,
        "body": json.dumps(event)
    }