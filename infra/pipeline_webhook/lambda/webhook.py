import json
import os
import boto3

client = boto3.client('codebuild')

def handler(event, context):
    body = event['body']
    body = json.loads(body)
    # If the Pull Request is not closed - let's do something
    if not body['pull_request']['closed_at']:
        # If the Pull Request is merged Zip up the source to S3 via CodeBuild else Lint the code
        if body['pull_request']['merged_at']:
            print('Kick off CodeBuild S3 Copy')
            #response = client.start_build(projectName='string')
        else:
            print('Kick off CodeBuild Lint')
            codebuild_project_functional = os.environ.get('codebuild_project_functional')
            client.start_build(projectName=codebuild_project_functional)
    return {
        "statusCode": 200,
        "body": json.dumps(event)
    }