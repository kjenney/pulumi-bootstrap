import sys
import os
import base64
import shutil
import pulumi
import pulumi_aws as aws
import pulumi_docker as docker

from common import manage

DOCKER_CONTEXT = "docker"

def create_docker_context():
    """Copy requirements.txt and Dockerfile from the root of the repo first
    for the Docker image build
    """
    os.mkdir(DOCKER_CONTEXT)
    #shutil.copyfile('../../requirements.txt', f"{DOCKER_CONTEXT}/requirements.txt")
    shutil.copyfile('requirements.txt', f"{DOCKER_CONTEXT}/requirements.txt")
    shutil.copyfile('Dockerfile', f"{DOCKER_CONTEXT}/Dockerfile")

def get_registry_info(rid):
    """Get registry info (creds and endpoint) so we can build/publish to it."""
    creds = aws.ecr.get_credentials(registry_id=rid)
    decoded = base64.b64decode(creds.authorization_token).decode()
    parts = decoded.split(':')
    if len(parts) != 2:
        raise Exception("Invalid credentials")
    return docker.ImageRegistry(creds.proxy_endpoint, parts[0], parts[1])

def pulumi_program():
    """Pulumi Program"""
    config = pulumi.Config()
    environment = config.require('environment')
    codebuild_image_repo = aws.ecr.Repository(f"codebuild-image-{environment}",
        image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
            scan_on_push=False,
        ))
    pulumi.export("codebuild_image_repo", codebuild_image_repo.id)

    aws.ecr.RepositoryPolicy("codebuild_image_repo_policy",
        repository=codebuild_image_repo.name,
        policy="""{
            "Version": "2008-10-17",
            "Statement": [
                {
                    "Sid": "CodeBuildAccessPrincipal",
                    "Effect": "Allow",
                    "Principal":{
                        "Service":"codebuild.amazonaws.com"
                    },
                    "Action": [
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:PutImage",
                        "ecr:InitiateLayerUpload",
                        "ecr:UploadLayerPart",
                        "ecr:CompleteLayerUpload",
                        "ecr:DescribeRepositories",
                        "ecr:GetRepositoryPolicy",
                        "ecr:ListImages",
                        "ecr:DeleteRepository",
                        "ecr:BatchDeleteImage",
                        "ecr:SetRepositoryPolicy",
                        "ecr:DeleteRepositoryPolicy"
                    ]
                }
            ]
        }""")


    registry = codebuild_image_repo.registry_id.apply(get_registry_info)

    ## Docker Image Build and Publish
    codebuild_image = docker.Image('bootstrap-image',
                    image_name=codebuild_image_repo.repository_url,
                    build=docker.DockerBuild(context=f'./{DOCKER_CONTEXT}'),
                    registry=registry
                    )
    pulumi.export("codebuild_image", codebuild_image.base_image_name)

def cleanup_docker_context():
    """Remove the docker context folder"""
    shutil.rmtree(DOCKER_CONTEXT)

# Deploy ECR Repo with Docker Image
def stacked(environment, action='deploy'):
    """Manage the stack"""
    create_docker_context()
    manage(os.path.basename(os.path.dirname(__file__)), environment, action, pulumi_program)
    cleanup_docker_context()

def test():
    """Test the stack"""
    print("Run something useful here")
