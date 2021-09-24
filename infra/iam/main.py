import argparse
import json
import pulumi
import pulumi_aws as aws
from pulumi import automation as auto
import sys
import yaml
import os

sys.path.append("../../shared")
from bootstrap import *

# Deploy CodePipeline with CodeBuild projects for each piece of infra

def pulumi_program():
    config = pulumi.Config()
    environment = config.require('environment')
    data = get_config(environment)
    infra_projects = data['infra']
    # Get S3 buckets
    s3_reference = pulumi.StackReference(f"s3-{environment}")
    buckets = {}
    for project in infra_projects:
        buckets[f"codebuild_{project}_bucket_id"] = s3_reference.get_output(f"codebuild_{project}_bucket_id")
    buckets["codepipeline_bucket_id"] = s3_reference.get_output("codepipeline_bucket_id")

    stmt = {'Version': '2012-10-17','Statement': []}
    stmt['Statement'] = {'Effect': 'Allow', 'Action': ['s3: *'], 'Resource': []}

    # Create the IAM Assume Roles
    codepipeline_role = aws.iam.Role(f"codepipelineRole-{environment}", assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Principal": {
                "Service": "codepipeline.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
            }
        ]
        }
    """)

    codebuild_role = aws.iam.Role(f"codebuildRole-{environment}", assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Principal": {
                "Service": "codepipeline.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
            }
        ]
        }
    """)

    codepipeline_policy = aws.iam.RolePolicy("codepipelinePolicy",
        role=codepipeline_role.id,
        policy=f"""{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                "Effect": "Allow",
                "Action": [
                    "codebuild:BatchGetBuilds",
                    "codebuild:BatchGetProjects",
                    "codebuild:StartBuild"
                ],
                "Resource": "*"
                }},
                {{
                    "Effect": "Allow",
                    "Action": ["kms:*"],
                    "Resource": [
                    "arn:aws:kms:us-east-1:161101091064:key/4ed7e926-9130-4259-a8b4-d2e033d31b5f"                
                    ]
                }}
            ]
            }}
            """)

    for key in buckets:
        codebuild_role_policy = aws.iam.RolePolicy(f"codebuildbucketpolicy-{key}",
            role=codebuild_role.name,
            policy=pulumi.Output.all(bucket=buckets[key]).apply(lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": ["s3:*"],
                    "Resource": [
                        "arn:aws:s3:::{args['bucket']}",
                        "arn:aws:s3:::{args['bucket']}/*"
                    ]
                }}
                ]
            }}
            """))
        codepipeline_role_policy = aws.iam.RolePolicy(f"codepipelinebucketpolicy-{key}",
            role=codepipeline_role.name,
            policy=pulumi.Output.all(bucket=buckets[key]).apply(lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": ["s3:*"],
                    "Resource": [
                        "arn:aws:s3:::{args['bucket']}",
                        "arn:aws:s3:::{args['bucket']}/*"
                    ]
                }}
                ]
            }}
            """))
    pulumi.export(f"codepipeline_role_arn", codepipeline_role.arn)
    pulumi.export(f"codepipeline_role_id", codepipeline_role.id)
    pulumi.export(f"codebuild_role_arn", codebuild_role.arn)
    pulumi.export(f"codebuild_role_id", codebuild_role.id)    

stack = manage(args(), 'iam', pulumi_program)

