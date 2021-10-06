import argparse
import json

from yaml.events import CollectionEndEvent
import pulumi
import pulumi_aws as aws
import pulumi_github as github
from pulumi import automation as auto
import sys
import yaml
import zipfile
import os

sys.path.append("../../shared")
from bootstrap import *

project_name = os.path.basename(os.getcwd())

### Deploy Lambda to Trigger CodeBuild Projects for testing and triggered CodePipeline on merge

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from typing import Union

def zip_dir(zip_name: str, source_dir: Union[str, os.PathLike]):
    src_path = Path(source_dir).expanduser().resolve(strict=True)
    with ZipFile(zip_name, 'w', ZIP_DEFLATED) as zf:
        for file in src_path.rglob('*'):
            zf.write(file, file.relative_to(src_path))

def pulumi_program():
    config = pulumi.Config()
    environment = config.require('environment')
    data = get_config(environment)
    infra_projects = data['infra']
    s3_stack = pulumi.StackReference(f"pipeline-s3-{environment}")
    codebuild_functional_bucket = s3_stack.get_output("codebuild_functional_bucket")
    codebuild_main_bucket = s3_stack.get_output("codebuild_main_bucket")

    label_tags = {
        "Project" : project_name,
        "ManagedBy"  : 'Pulumi',
        "Environment": environment,
    }

    # Export GitHub Token to provision the Webhook
    secrets = pulumi.StackReference(f"secrets-{environment}")
    github_token = secrets.get_output("github_token")
    github_provider = github.Provider(resource_name='github_provider', token=github_token)
    
    # Create Secrets Manager secret with GitHub Token for the CodeBuild jobs
    github_token_secret = aws.secretsmanager.Secret("webhook-github-token-secret",
        name=f"webhook-github-token-secret-{environment}",
        description="The GitHub Token for use by CodeBuild projects to test and build source from GitHub code",
        tags=label_tags
    )

    github_token_secret_value = aws.secretsmanager.SecretVersion(f"webhook-github-token-secret-value",
        secret_id=github_token_secret.id,
        secret_string=github_token)

    # Create the IAM Role to give the CodeBuild Jobs access to the github_token_secret
    codebuild_role = aws.iam.Role("codebuldRole", assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Principal": {
                "Service": "codebuild.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
            }
        ]
        }
    """)

    codebuild_policy = aws.iam.RolePolicy("codebuldPolicy",
        role=codebuild_role.id,
        policy=pulumi.Output.all(github_token_secret=github_token_secret.arn).apply(lambda args: f"""{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:*"
                    ],
                    "Resource": "{args['github_token_secret']}"
                }},
                {{
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": ["*"]
                }}
            ]
        }}
    """))

    codebuild_project_functional = aws.codebuild.Project("codebuild-functional-testing",
        description=f"codebuild project for {project_name} in {environment}",
        build_timeout=5,
        service_role=codebuild_role.arn,
        artifacts=aws.codebuild.ProjectArtifactsArgs(
            type="NO_ARTIFACTS",
        ),
        environment=aws.codebuild.ProjectEnvironmentArgs(
            compute_type="BUILD_GENERAL1_SMALL",
            image="aws/codebuild/standard:1.0",
            type="LINUX_CONTAINER",
            image_pull_credentials_type="CODEBUILD",
        ),
        logs_config=aws.codebuild.ProjectLogsConfigArgs(
            cloudwatch_logs=aws.codebuild.ProjectLogsConfigCloudwatchLogsArgs(
                group_name="log-group",
                stream_name="log-stream",
            )
        ),
        source=aws.codebuild.ProjectSourceArgs(
            type="S3",
            location=codebuild_functional_bucket.apply(lambda id: f"{id}/")
        ),
        tags=label_tags
    )

    codebuild_project_main = aws.codebuild.Project("codebuild-clone-main",
        description=f"codebuild project for {project_name} in {environment}",
        build_timeout=5,
        service_role=codebuild_role.arn,
        artifacts=aws.codebuild.ProjectArtifactsArgs(
            type="NO_ARTIFACTS",
        ),
        environment=aws.codebuild.ProjectEnvironmentArgs(
            compute_type="BUILD_GENERAL1_SMALL",
            image="aws/codebuild/standard:1.0",
            type="LINUX_CONTAINER",
            image_pull_credentials_type="CODEBUILD",
        ),
        logs_config=aws.codebuild.ProjectLogsConfigArgs(
            cloudwatch_logs=aws.codebuild.ProjectLogsConfigCloudwatchLogsArgs(
                group_name="log-group",
                stream_name="log-stream",
            )
        ),
        source=aws.codebuild.ProjectSourceArgs(
            type="S3",
            location=codebuild_main_bucket.apply(lambda id: f"{id}/")
        ),
        tags=label_tags
    )

    # Create CloudWatch Event Rule to Pick Up S3 Object Upload and Trigger CodeBuild Job
    check_s3_functional = aws.cloudwatch.EventRule("check_s3_objects_in_functional_bucket",
        description="Capture when Lambda uploads buildspec in the functional bucket",
        event_pattern=pulumi.Output.all(codebuild_functional_bucket=codebuild_functional_bucket).apply(lambda args: f"""{{
            "source": [
                "aws.s3"
            ],
            "detail-type": [
                "AWS API Call via CloudTrail"
            ],
            "detail": {{
                "eventSource": [
                    "s3.amazonaws.com"
                ],
                "eventName": [
                    "PutObject"
                ],
                "requestParameters": {{
                "bucketName": [
                    "{args['codebuild_functional_bucket']}"
                ]
                }}
            }}
        }}"""))

    check_s3_main = aws.cloudwatch.EventRule("check_s3_objects_in_main_bucket",
        description="Capture when Lambda uploads buildspec in the main bucket",
        event_pattern=pulumi.Output.all(codebuild_main_bucket=codebuild_main_bucket).apply(lambda args: f"""{{
            "source": [
                "aws.s3"
            ],
            "detail-type": [
                "AWS API Call via CloudTrail"
            ],
            "detail": {{
                "eventSource": [
                    "s3.amazonaws.com"
                ],
                "eventName": [
                    "PutObject"
                ],
                "requestParameters": {{
                "bucketName": [
                    "{args['codebuild_main_bucket']}"
                ]
                }}
            }}
        }}"""))

    # Create the IAM Roles to allow Events to Trigger CodeBuild jobs
    trigger_codebuild_functional_role = aws.iam.Role("trigger_codebuild_functional_role", assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Principal": {
                "Service": "events.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
            }
        ]
        }
    """)

    trigger_codebuild_functional_policy = aws.iam.RolePolicy("trigger_codebuild_functional_policy",
        role=codebuild_role.id,
        policy=pulumi.Output.all(codebuild_project_functional_arn=codebuild_project_functional.arn).apply(lambda args: f"""{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": [
                        "codebuild:StartBuild"
                    ],
                    "Resource": ["{args['codebuild_project_functional_arn']}"]
                }}
            ]
        }}
    """))

    trigger_codebuild_main_role = aws.iam.Role("trigger_codebuild_main_role", assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Principal": {
                "Service": "events.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
            }
        ]
        }
    """)

    trigger_codebuild_main_policy = aws.iam.RolePolicy("trigger_codebuild_main_policy",
        role=codebuild_role.id,
        policy=pulumi.Output.all(codebuild_project_main_arn=codebuild_project_main.arn).apply(lambda args: f"""{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": [
                        "codebuild:StartBuild"
                    ],
                    "Resource": ["{args['codebuild_project_main_arn']}"]
                }}
            ]
        }}
    """))

    trigger_codebuild_functional = aws.cloudwatch.EventTarget("trigger_codebuild_functional",
        rule=check_s3_functional.name,
        arn=codebuild_project_functional.arn,
        role_arn=trigger_codebuild_functional_role.arn
    )

    trigger_codebuild_main = aws.cloudwatch.EventTarget("trigger_codebuild_main",
        rule=check_s3_main.name,
        arn=codebuild_project_main.arn,
        role_arn=trigger_codebuild_main_role.arn
    )

    # Create the role for the Lambda to assume
    lambda_role = aws.iam.Role("lambda-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                    "Action": "sts:AssumeRole",
                    "Principal": {
                        "Service": "lambda.amazonaws.com",
                    },
                    "Effect": "Allow",
                    "Sid": "",
                }]
        }),
        tags = label_tags,
    )

    lambda_policy = aws.iam.RolePolicy("lambda-policy",
        role=lambda_role.id,
        policy=pulumi.Output.all(codebuild_functional_bucket=codebuild_functional_bucket,codebuild_main_bucket=codebuild_main_bucket).apply(lambda args: f"""{{
                    "Version": "2012-10-17",
                    "Statement": [
                    {{
                        "Effect": "Allow",
                        "Action": ["s3:*"],
                        "Resource": [
                            "arn:aws:s3:::{args['codebuild_functional_bucket']}",
                            "arn:aws:s3:::{args['codebuild_functional_bucket']}/*",
                            "arn:aws:s3:::{args['codebuild_main_bucket']}",
                            "arn:aws:s3:::{args['codebuild_main_bucket']}/*"
                        ]
                    }}
                    ]
                }}
                """))

    # Attach the fullaccess policy to the Lambda role created above
    role_policy_attachment = aws.iam.RolePolicyAttachment("lambdaRoleAttachment",
        role=lambda_role,
        policy_arn=aws.iam.ManagedPolicy.AWS_LAMBDA_BASIC_EXECUTION_ROLE)

    # Zip up the code with dependencies
    zip_dir('/tmp/source.zip','./lambda')

    # Create the lambda to execute
    lambda_function = aws.lambda_.Function(f"lambda-function-{environment}",
        code=pulumi.FileArchive('/tmp/source.zip'),
        runtime="python3.8",
        role=lambda_role.arn,
        handler="webhook.handler",
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={
                "environment": environment,
                "projects": ','.join(infra_projects),
                "s3_bucket_functional": codebuild_functional_bucket,
                "s3_bucket_main": codebuild_main_bucket,  
            },
        ))

    # Give API Gateway permissions to invoke the Lambda
    lambda_permission = aws.lambda_.Permission("lambdaPermission",
        action="lambda:InvokeFunction",
        principal="apigateway.amazonaws.com",
        function=lambda_function)

    # Set up the API Gateway
    apigw = aws.apigatewayv2.Api(f"httpApiGateway-{environment}",
        protocol_type="HTTP",
        route_key="POST /",
        target=lambda_function.invoke_arn)

    pulumi.export('api_base_url', apigw.api_endpoint)
    pulumi.export(f"lambda_function_arn", lambda_function.arn)

    # Register webhook
    webhook = github.RepositoryWebhook(f"bootstrap-webhook-{environment}",
        repository='pulumi-bootstrap',
        configuration=github.RepositoryWebhookConfigurationArgs(
            url=apigw.api_endpoint,
            content_type="json",
            insecure_ssl=False,
        ),
        active=True,
        events=["pull_request"],
        opts=pulumi.ResourceOptions(provider=github_provider))

stack = manage(args(), project_name, pulumi_program)