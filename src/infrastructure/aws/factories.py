import boto3


def build_dynamodb_resource():
    return boto3.resource("dynamodb")


def build_s3_client():
    return boto3.client("s3")
