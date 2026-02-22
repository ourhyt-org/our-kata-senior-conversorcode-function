# Function B - SQS Worker Lambda

This project implements AWS Lambda Function B in Python 3.13 using Clean Architecture.

## What it does

- Consumes SQS messages with conversion jobs.
- Reads request metadata and source code from S3.
- Calls MCP HTTP conversion service.
- Packages converted artifacts into `output.zip` and creates `report.json`.
- Uploads outputs to S3.
- Updates job state in DynamoDB with idempotent-safe behavior.
- Returns SQS partial batch failures so only failed records retry.

## Environment variables

- `DDB_TABLE` (required): DynamoDB table name storing job status.
- `OUTPUT_BUCKET` (required): S3 bucket where output artifacts are written.
- `MCP_BASE_URL` (optional): fallback MCP URL if missing from SQS message.
- `MAX_FILES` (optional, default `200`): max number of output files accepted from MCP.
- `MAX_ZIP_MB` (optional, default `50`): max zip size (and uncompressed aggregate limit) in MB.
- `LOG_LEVEL` (optional, default `INFO`): logger level.

## Handler

- Lambda handler: `src.interfaces.lambda_handler.handler.lambda_handler`

## Local development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest -q
```

## Deployment note

- Runtime: Python 3.13
- Package `src/` and all dependencies in the Lambda deployment artifact.
- Configure Lambda timeout close to expected max processing window (for example 900 seconds).
- Ensure IAM role permissions for SQS trigger, DynamoDB table access, and S3 read/write.
