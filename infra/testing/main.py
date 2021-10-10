import sys
import os
import pulumi
import pulumi_aws as aws
from s3 import Bucket, BucketArgs

from bootstrap import manage

def pulumi_program():
    """Pulumi Program"""
    config = pulumi.Config()
    environment = config.require('environment')
    project_name = config.require('project_name')
    bucket = Bucket('test',
        BucketArgs(
            environment=environment,
            project_name=project_name,
            principal='codebuild'
        ))
    pulumi.export("bucket_id", bucket.bucket_id)
    pulumi.export("bucket_builder_role_arn", bucket.assume_role)

def stacked(environment, action='deploy'):
    """Manage the stack"""
    manage(os.path.basename(os.path.dirname(__file__)), environment, action, pulumi_program)

def test():
    """Test the stack"""
    print("Run something useful here")

