# pulumi-bootstrap-secrets

Store secrets encrypted in a Pulumi stack with secrets encrypted in-place usign Pulumi Automation and KMS

## Updating secrets

To update secrets decrypt the file first:

```
python decrypt.py
```

Update secrets then re-encrypt the file:

```
python encrypt.py
```