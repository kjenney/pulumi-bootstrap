import json
import os

def handler(event, context):
    print('## EVENT')
    print(event)
    # If the Pull Request is not closed - let's do something
    if event['closed_at'] != 'null':
        # If the Pull Request is merged Zip up the source to S3 via CodeBuild else Lint the code
        if event['merged_at'] != 'null':
            print('Kick off CodeBuild S3 Copy')
        else:
            print('Kick off CodeBuild Lint')
    return {
        "statusCode": 200,
        "body": json.dumps(event)
    }