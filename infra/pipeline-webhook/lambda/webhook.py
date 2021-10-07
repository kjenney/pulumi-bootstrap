import json
import os
from datetime import datetime
import boto3
import yaml

s3 = boto3.resource(
    's3',
    region_name='us-east-1'
)

environment = os.environ.get('environment')
dt1 = datetime.now()

def buildspec_functional(environ, branch, sha):
    """Create the CodeBuild Job that will be used for Functional Testing"""
    return {'version': '0.2',
            'env': {
                'secrets-manager': {
                    'GITHUB_TOKEN': f"webhook-github-token-secret3-{environ}"
                }
            },
            'phases': {
                'install': {
                    'runtime-versions': {
                        'python': '3.x'
                    },
                    'commands': [
                        'curl -fsSL https://get.pulumi.com | sh',
                        'PATH=$PATH:/root/.pulumi/bin'
                    ]
                },
                'pre_build': {
                    'commands': [
                        f"git clone --branch {branch} https://$GITHUB_TOKEN@github.com/kjenney/pulumi-bootstrap.git"
                    ]
                },
                'build': {
                    'commands': [
                        'cd pulumi-bootstrap',
                        'pwd',
                        'pip install -r requirements.txt',
                        f"./check_status.sh $GITHUB_TOKEN {sha}"
                    ]
                }
            }}

def buildspec_main(environ):
    """Create the CodeBuild Job that will be used to clone the main branch"""
    return {'version': '0.2',
            'env': {
                'secrets-manager': {
                    'GITHUB_TOKEN': f"webhook-github-token-secret-{environ}"
                }
            },
            'phases': {
                'install': {
                    'runtime-versions': {
                        'python': '3.x'
                    },
                    'commands': [
                        'curl -fsSL https://get.pulumi.com | sh',
                        'PATH=$PATH:/root/.pulumi/bin'
                    ]
                },
                'pre_build': {
                    'commands': [
                        "git clone https://$(GITHUB_TOKEN)@github.com/kjenney/pulumi-bootstrap.git"
                    ]
                },
                'build': {
                    'commands': [
                        'cd pulumi-bootstrap',
                        'pip install -r requirements.txt'
                        "pylint $(git ls-files '*.py')"
                    ]
                }
            },
            'artifacts': {
                'files': [
                    '**/*'
                ],
                'name': 'pulumi-bootstrap',
                'base-directory': './pulumi-bootstrap',
                'discard-paths': 'yes'
            }
        }

def compare_times(one_time, another_time):
    """Function to compare one time to another time and return the difference in seconds"""
    another_time_dt = datetime.strptime(another_time, "%Y-%m-%dT%H:%M:%SZ")
    diff =  one_time - another_time_dt
    return diff.seconds

def handler(event, context):
    """Gets PR events
    Check to see if the PR is open
    Write an object to S3 which triggers one of two jobs
    """
    print("CloudWatch log stream name:", context.log_stream_name)
    body = event['body']
    body = json.loads(body)
    # If the Pull Request was merged within the last 30 seconds let's assume we want to build it
    if body['pull_request']['merged_at']:
        if compare_times(datetime.utcnow(), body['pull_request']['merged_at']) < 30:
            print('Trying to tell where the label is')
            if body['pull_request']['base']['label'] == 'kjenney:main':
                print('Label matches up')
            else:
                print('Label does not match up')
            #     print('Copy buildspec to S3 bucket to kick off CodeBuild for Main Clone')
            #     s3_bucket_main = os.environ.get('s3_bucket_main')
            #     buildspec = buildspec_main(environment)
            #     content=yaml.dump(buildspec, indent=4, default_flow_style=False)
            #     s3.Object(s3_bucket_main, 'buildspec.yml').put(Body=content)
            # else:
            #     print('Pull Request was not merged into main. Aborting')
        else:
            print('Pull Request was merged more than 30 seoconds ago. Aborting')
    else:
        print('Copy buildspec to S3 bucket to kick off CodeBuild for Functional Testing')
        s3_bucket_functional = os.environ.get('s3_bucket_functional')
        # Branch metadata includes origin and branch - splitting the string to only include the branch
        branch = body['pull_request']['head']['label'].split(':')[1]
        # Get the Commit SHA for reporting the status once the build has completed
        sha = body['pull_request']['head']['sha']
        buildspec = buildspec_functional(environment, branch, sha)
        content=yaml.dump(buildspec, indent=4, default_flow_style=False)
        s3.Object(s3_bucket_functional, 'buildspec.yml').put(Body=content)
    return {
        "statusCode": 200,
        "body": json.dumps(event)
    }
