import sys
import os
import base64
from shutil import copyfile
import pulumi
import pulumi_aws as aws
import pulumi_docker as docker

sys.path.append("../..//shared")
from bootstrap import manage, args

# Copy requirements.txt from the root of the repo first - for the Docker image build
CUSTOM_IMAGE = "pulumi-bootstrap"
copyfile('../../requirements.txt', f"{CUSTOM_IMAGE}/requirements.txt")

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
    codebuild_image = docker.Image(f"{CUSTOM_IMAGE}-{environment}",
                    image_name=codebuild_image_repo.repository_url,
                    build=docker.DockerBuild(context=f'./{CUSTOM_IMAGE}'),
                    registry=registry
                    )
    pulumi.export("codebuild_image", codebuild_image.base_image_name)

# Deploy ECR Repo with Docker Image
stack = manage(args(), os.path.basename(os.getcwd()), pulumi_program)
