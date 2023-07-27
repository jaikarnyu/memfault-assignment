"""
Global Configuration for Application
"""
import os
import json
import logging

# Get configuration from environment
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@postgres:5432/postgres"
)

# DATABASE_URI = "postgresql://postgres:postgres@database-1.cohpvrnkweup.us-east-1.rds.amazonaws.com:5432/postgres"
print(DATABASE_URI)

# override if we are running in Cloud Foundry
if "VCAP_SERVICES" in os.environ:
    vcap = json.loads(os.environ["VCAP_SERVICES"])
    DATABASE_URI = vcap["user-provided"][0]["credentials"]["url"]

# Configure SQLAlchemy
SQLALCHEMY_DATABASE_URI = DATABASE_URI
SQLALCHEMY_TRACK_MODIFICATIONS = False
# SQLALCHEMY_POOL_SIZE = 2

# Secret for session management
SECRET_KEY = os.getenv("SECRET_KEY", "sup3r-s3cr3t")
LOGGING_LEVEL = logging.INFO


# AWS Credentials
AWS_ACCESS_KEY = os.getenv("aws_access_key_id", "AKIAUXHD6LSDRNOOLW7Z")
AWS_SECRET_KEY = os.getenv(
    "aws_secret_access_key", "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"
)
AWS_S3_BUCKET = os.getenv("aws_s3_bucket", "webbotexperiments")
AWS_S3_PREFIX = os.getenv("aws_s3_prefix", "webbot/{webbot_id}/")
AWS_REGION = os.getenv("aws_region", "us-east-1")


LOCAL_FILE_PATH = os.getenv("LOCAL_FILE_PATH", "/tmp/webbot/{webbot_id}/")
DOWNLOADS_PATH = os.getenv("DOWNLOADS_PATH", "/tmp/webbot/{webbot_id}/downloads/")
ALLOWED_EXTENSIONS = set(["txt", "pdf", "png", "jpg", "jpeg", "csv"])

# create directory /tmp/webbot
if not os.path.exists("/tmp/webbot"):
    os.makedirs("/tmp/webbot")
