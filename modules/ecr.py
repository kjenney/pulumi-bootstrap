import os
import base64
import shutil
from pulumi import ComponentResource, ResourceOptions, Output
import pulumi_aws as aws
import pulumi_docker as docker

class ECRRepoArgs:
    """ECR Repo Arguments"""
    def __init__(self,
                environment=None,
                project_name=None,
                scan_on_push=False,
                context='docker'
                ):
        self.environment = environment
        self.project_name = project_name
        self.scan_on_push = scan_on_push
        self.context = context

class ECRRepo(ComponentResource):
    """
    Create an ECR Repository with permissions granted to an AWS Principal
    Optionally build and push a Docker image to this ECR Repository
    """
    def __init__(self, name, args=ECRRepoArgs, opts: ResourceOptions = None):
        super().__init__('pkg:index:ECR', name, None, opts)
        name = f"{name}-{args.project_name}-{args.environment}"
        repo = aws.ecr.Repository(name,
            image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
                scan_on_push=False,
            ))
        registry = repo.registry_id.apply(self.get_registry_info)
         ## Docker Image Build and Publish
        image = docker.Image('image',
                        image_name=repo.repository_url,
                        build=docker.DockerBuild(context=f'./{args.context}'),
                        registry=registry
                        )
        assumed_policy = aws.iam.Policy("policy",
            path="/",
            description="IAM Policy that is assumed to create resources in the {args.project_name} stack",
            policy=Output.all(repo=repo.arn).apply(lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                {{
                    "Effect": "Allow",
                    "Action": ["ecr:*"],
                    "Resource": ["arn:aws:s3:::{args['repo']}"]
                }}
                ]
            }}"""
        ))
        self.repo_id = repo.id
        self.image_name = image.base_image_name
        self.assume_policy_id = assumed_policy.id
        self.assume_policy_arn = assumed_policy.arn
        self.register_outputs({})

    def get_registry_info(self, rid):
        """Get registry info (creds and endpoint) so we can build/publish to it."""
        creds = aws.ecr.get_credentials(registry_id=rid)
        decoded = base64.b64decode(creds.authorization_token).decode()
        parts = decoded.split(':')
        if len(parts) != 2:
            raise Exception("Invalid credentials")
        return docker.ImageRegistry(creds.proxy_endpoint, parts[0], parts[1])