1. Update CodeBuild PR Projects to use the Secret to clone the repo and run lint, tests, etc
2. Create a new CodeBuild Project to fetch main and create a zip in S3 - triggered by Webhook Lambda
3. Update CodePipeline to use the s3 zip as source