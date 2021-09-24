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

# Deploy S3 buckets to support pieces of infra

def pulumi_program():
    config = pulumi.Config()
    environment = config.require('environment')
    data = get_config(environment)
    infra_projects = data['infra']
    for project in infra_projects:
        codebuild_bucket = aws.s3.Bucket(
            f"codeBuildBucket-{project}-{environment}", 
            acl="private",
            tags={
                "Environment": environment,
                "Managed By": "Pulumi",
                "Name": f"codeBuildBucket-{project}-{environment}",
            }
        )
        pulumi.export(f"codebuild_{project}_bucket_id", codebuild_bucket.id)

    codepipeline_bucket = aws.s3.Bucket(
        f"codePipelineBucket-{environment}", 
        acl="private",
        tags={
            "Environment": environment,
            "Managed By": "Pulumi",
            "Name": f"codeBuildBucket-{environment}",
        }
    )
    pulumi.export(f"codepipeline_bucket_id", codepipeline_bucket.id)

stack = manage(args(), 's3', pulumi_program)


