import sys
import os
import pulumi
import pulumi_aws as aws
from s3 import Bucket, BucketArgs
from codebuild import CodeBuildProject, CodeBuildProjectArgs
from common import AutoTag, manage

def pulumi_program():
    """Pulumi Program"""
    config = pulumi.Config()
    environment = config.require('environment')
    project_name = pulumi.get_project()
    #ecr_reference = pulumi.StackReference(f"pipeline-ecr-{environment}")
    codebuild_image = 'python'
    AutoTag(environment)
    codebuild = CodeBuildProject('test',
        CodeBuildProjectArgs(
            environment=environment,
            project_name=project_name,
            codebuild_image=codebuild_image
        ))

def stacked(environment, action='deploy'):
    """Manage the stack"""
    manage(os.path.basename(os.path.dirname(__file__)), environment, action, pulumi_program)

def test():
    """Test the stack"""
    print("Run something useful here")

