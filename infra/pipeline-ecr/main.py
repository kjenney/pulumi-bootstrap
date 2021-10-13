import os
import base64
import shutil
import pulumi
import pulumi_aws as aws
import pulumi_docker as docker
from ecr import ECRRepo, ECRRepoArgs
from codebuild import CodeBuildProject, CodeBuildProjectArgs
from common import AutoTag, manage

def create_docker_context(context):
    """Copy requirements.txt and Dockerfile from the root of the repo first
    for the Docker image build
    """
    os.mkdir(context)
    shutil.copyfile('requirements.txt', f"{context}/requirements.txt")
    shutil.copyfile('Dockerfile', f"{context}/Dockerfile")

def cleanup_docker_context(context):
    """Remove the docker context folder"""
    shutil.rmtree(context)

def pulumi_program():
    """Pulumi Program"""
    config = pulumi.Config()
    environment = config.require('environment')
    project_name = pulumi.get_project()
    AutoTag(environment)
    context = 'docker'
    #os.mkdir(context)
    repo = ECRRepo('codebuild_image',
            ECRRepoArgs(
                environment=environment,
                project_name=project_name,
                context=context
            ))
    assumed_role = aws.iam.Role(f"assumeRole-{project_name}-{environment}", assume_role_policy=f"""{{
        "Version": "2012-10-17",
        "Statement": [
        {{
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Principal": {{
                "Service": "codebuild.amazonaws.com"
            }}
        }}
        ]
        }}""")
    aws.iam.RolePolicyAttachment("codebuild-attach",
        role=assumed_role.name,
        policy_arn=repo.assume_policy_arn)
    codebuild_project = CodeBuildProject('pipeline-ecr',
        CodeBuildProjectArgs(
            environment=environment,
            project_name=project_name,
            codebuild_image=repo.image_name,
            assumed_role_id=assumed_role.id,
            assumed_role_arn=assumed_role.arn
        ))
    pulumi.export("image_repo", repo.repo_id)
    pulumi.export("image_name", repo.image_name)
    pulumi.export("assume_policy_id", repo.assume_policy_id)
    pulumi.export("project_arn", codebuild_project.project_arn)

def stacked(environment, action='deploy'):
    """Manage the stack"""
    create_docker_context('docker')
    manage(os.path.basename(os.path.dirname(__file__)), environment, action, pulumi_program)
    cleanup_docker_context('docker')

def test():
    """Test the stack"""
    print("Run something useful here")
