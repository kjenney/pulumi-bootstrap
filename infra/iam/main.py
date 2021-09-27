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
    # Grant access to every bucket for CodePipeline
    for key in buckets:
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
    # Grant access to codebuild projects
    for project_name in infra_projects:
        codebuild_role = aws.iam.Role(f"codebuildRole-{project_name}-{environment}", assume_role_policy="""{
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
        pulumi.export(f"codebuild_role_{project_name}_arn", codebuild_role.arn)
        pulumi.export(f"codebuild_role_{project_name}_id", codebuild_role.id)
        for key in buckets:
            codebuild_bucket_policy = aws.iam.RolePolicy(f"codeBuildBucketRolePolicy-{project_name}-{key}-{environment}",
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
        codebuild_role_policy = aws.iam.RolePolicy(f"codeBuildRolePolicy-{project_name}-{environment}",
            role=codebuild_role.name,
            policy=f"""{{
                "Version": "2012-10-17",
                "Statement": [
                {{
                    "Effect": "Allow",
                    "Resource": ["*"],
                    "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                    ]
                }},
                {{
                    "Effect": "Allow",
                    "Resource": "*",
                    "Action": [
                    "ec2:CreateNetworkInterface",
                    "ec2:CreateNetworkInterfacePermission",
                    "ec2:DescribeDhcpOptions",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DeleteNetworkInterface",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeVpcs"
                    ]
                }},
                {{
                    "Effect": "Allow",
                    "Action": ["s3:*"],
                    "Resource": [
                    "arn:aws:s3:::my-pulumi-state",
                    "arn:aws:s3:::my-pulumi-state/*"
                    ]
                }},
                {{
                    "Effect": "Allow",
                    "Action": ["kms:*"],
                    "Resource": [
                    "arn:aws:kms:us-east-1:161101091064:key/4ed7e926-9130-4259-a8b4-d2e033d31b5f"                
                    ]
                }},
                {{
                    "Effect": "Allow",
                    "Action": [
                        "iam:ListRolePolicies",
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:ListAttachedRolePolicies"
                    ],
                    "Resource": "*"
                }},
                {{
                    "Effect": "Allow",
                    "Action": [
                        "ec2:*"
                    ],
                    "Resource": "*"                
                }},
                {{
                    "Effect": "Allow",
                    "Action": [
                        "codebuild:BatchGetProjects"
                    ],
                    "Resource": "*"
                }},
                {{
                    "Effect": "Allow",
                    "Action": [
                        "codepipeline:GetPipeline",
                        "codepipeline:ListTagsForResource"
                    ],
                    "Resource": "*"
                }}
                ]
            }}
        """)
    pulumi.export(f"codepipeline_role_arn", codepipeline_role.arn)
    pulumi.export(f"codepipeline_role_id", codepipeline_role.id)

stack = manage(args(), 'iam', pulumi_program)

