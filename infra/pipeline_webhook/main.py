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

# Deploy Lambda to Trigger CodeBuild Projects for testing and triggered CodePipeline on merge

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

    label_tags = {
        "Project" : project_name,
        "ManagedBy"  : 'Pulumi',
        "Environment": environment,
    }

    id = "-".join(label_tags.values())

    # Export GitHub Token to provision the Webhook
    secrets = pulumi.StackReference(f"secrets-{environment}")
    github_token = secrets.get_output("github_token")
    github_provider = github.Provider(resource_name='github_provider', token=github_token)
    
    # Create Secrets Manager secret with GitHub Token for the CodeBuild jobs
    github_token_secret = aws.secretsmanager.Secret(f"{id}-webhook-github-token-secret",
        name="webhook-github-token-secret",
        description="The GitHub Token for use by CodeBuild projects to test and build source from GitHub code",
        tags=label_tags
    )

    github_token_secret_value = aws.secretsmanager.SecretVersion(f"{id}-webhook-github-token-secret-value",
        secret_id=github_token_secret.id,
        secret_string=github_token)


    # Create the S3 Buckets that will be used by the Lambda and CodeBuild
    codebuild_functional_bucket = aws.s3.Bucket(f"codebuild-functional-{environment}", 
        acl="private",
        tags=label_tags
    )

    codebuild_main_bucket = aws.s3.Bucket(f"codebuild-main-{environment}",
        acl="private",
        tags=label_tags
    )

    pulumi.export("codebuild_functional_bucket_id",codebuild_functional_bucket.id)
    pulumi.export("codebuild_main_bucket_id",codebuild_main_bucket.id)

    # Create the IAM Role to give the CodeBuild Jobs access to the github_token_secret
    codebuild_role = aws.iam.Role(f"{id}-codebuldRole", assume_role_policy="""{
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

    codebuild_policy = aws.iam.RolePolicy(f"{id}-codebuldPolicy",
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

    codebuild_project_functional = aws.codebuild.Project(f"{id}-codebuild-functional-testing",
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
            location=codebuild_functional_bucket.id.apply(lambda id: f"{id}/"),

        ),
        tags=label_tags
    )

    codebuild_project_main = aws.codebuild.Project(f"{id}-codebuild-clone-main",
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
            location=codebuild_main_bucket.id.apply(lambda id: f"{id}/"),

        ),
        tags=label_tags
    )

    # Create the role for the Lambda to assume
    lambda_role = aws.iam.Role(f"{id}-lambda-role",
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

    lambda_policy = aws.iam.RolePolicy(f"{id}-lambda-policy",
        role=lambda_role.id,
        policy=pulumi.Output.all(codebuild_functional_bucket=codebuild_functional_bucket.id,codebuild_main_bucket=codebuild_main_bucket.id).apply(lambda args: f"""{{
                    "Version": "2012-10-17",
                    "Statement": [
                    {{
                        "Effect": "Allow",
                        "Action": ["s3:*"],
                        "Resource": [
                            "arn:aws:s3:::{args['codebuild_functional_bucket']}",
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
    lambda_function = aws.lambda_.Function(f"{id}-lambda-function",
        code=pulumi.FileArchive('/tmp/source.zip'),
        runtime="python3.8",
        role=lambda_role.arn,
        handler="webhook.handler",
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={
                "projects": ','.join(infra_projects),
                "s3_bucket_functional": codebuild_functional_bucket.id,
                "s3_bucket_main": codebuild_main_bucket.id
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