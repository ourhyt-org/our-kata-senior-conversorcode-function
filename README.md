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
- `MCP_AWS_IAM_AUTH` (optional, default `false`): when `true`, signs MCP HTTP requests with SigV4 (`service=lambda`), useful for Lambda Function URL with `AWS_IAM`.
- `MCP_AWS_REGION` (optional): region used for SigV4 signing. Defaults to `AWS_REGION` if present.
- `MCP_USE_MOCK` (optional, default `false`): when `true`, uses an internal mock MCP client.
- `MCP_MOCK_MODE` (optional, default `ok`): mock behavior, allowed values `ok`, `warning`, `error`.
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

## Test SQS event

Use this as Lambda test event:

```json
{
  "Records": [
    {
      "messageId": "msg-1",
      "receiptHandle": "AQEBexample",
      "body": "{\"jobId\":\"20e28f8e-4220-433b-9ef9-744720f31020\",\"requestS3Bucket\":\"my-input-bucket\",\"requestS3Key\":\"conversions/20e28f8e-4220-433b-9ef9-744720f31020/request.json\",\"codeS3Bucket\":\"my-input-bucket\",\"codeS3Key\":\"conversions/20e28f8e-4220-433b-9ef9-744720f31020/input.cob\",\"mcp\":{\"baseUrl\":\"https://mcp-service.example/convert\",\"tool\":\"convert_code\"}}",
      "attributes": {
        "ApproximateReceiveCount": "1",
        "SentTimestamp": "1735689600000",
        "SenderId": "AIDAEXAMPLE",
        "ApproximateFirstReceiveTimestamp": "1735689601000"
      },
      "messageAttributes": {},
      "md5OfBody": "d41d8cd98f00b204e9800998ecf8427e",
      "eventSource": "aws:sqs",
      "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:conversion-queue",
      "awsRegion": "us-east-1"
    }
  ]
}
```

The raw SQS `body` value is:

```json
{
  "jobId": "20e28f8e-4220-433b-9ef9-744720f31020",
  "requestS3Bucket": "my-input-bucket",
  "requestS3Key": "conversions/20e28f8e-4220-433b-9ef9-744720f31020/request.json",
  "codeS3Bucket": "my-input-bucket",
  "codeS3Key": "conversions/20e28f8e-4220-433b-9ef9-744720f31020/input.cob",
  "mcp": {
    "baseUrl": "https://mcp-service.example/convert",
    "tool": "convert_code"
  }
}
```

## Minimum IAM permissions

- DynamoDB: `dynamodb:GetItem`, `dynamodb:UpdateItem` on `DDB_TABLE`.
- S3 input bucket: `s3:GetObject`, `s3:HeadObject`.
- S3 output bucket: `s3:PutObject`, `s3:HeadObject`.
- CloudWatch Logs: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`.

## Deployment note

- Runtime: Python 3.13
- Package `src/` and all dependencies in the Lambda deployment artifact.
- Configure Lambda timeout close to expected max processing window (for example 900 seconds).
- Ensure IAM role permissions for SQS trigger, DynamoDB table access, and S3 read/write.
