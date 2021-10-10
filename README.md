# pulumi-bootstrap

## What is this for?

To Deploy Infrastructure on AWS using Pulumi while keeping secrets encrypted in code.

---

## Why do we do this?

Because we always expect our Infrastructure and Secrets will get out of control. By keeping secrets encrypted in code this allows us to audit, rotate, version, and test them. Pulumi extends pure code so we can build stacks that are highly extensible.

---

## Depdencies

* Docker
* aws-vault
* S3 Bucket and KMS Key for Pulumi State (see s3-state folder)

```
docker build -t bootstrap .
```

## To Deploy Everything (to the dev stack)

```
docker run -it --rm \
    --env-file <(aws-vault exec me -- env | grep ^AWS_) \
    --env-file .env \
    --mount type=bind,source="$(pwd)",target=/bootstrap \
    -v /var/run/docker.sock:/var/run/docker.sock \
    bootstrap deploy.py -e dev
```

## To Destroy Everything (to the dev stack)

```
docker run -it --rm \
    --env-file <(aws-vault exec me -- env | grep ^AWS_) \
    --env-file .env \
    --mount type=bind,source="$(pwd)",target=/bootstrap \
    -v /var/run/docker.sock:/var/run/docker.sock \
    bootstrap destroy.py -e dev
```

