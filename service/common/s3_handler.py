import os
import boto3
from service.config import AWS_ACCESS_KEY, AWS_SECRET_KEY
from botocore.exceptions import ClientError
import logging

# Get configuration from environment


class S3Handler(object):
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name="us-east-1",
        )

    def upload_files(self, local_path, bucket, prefix):

        """Upload a file to an S3 bucket

        :param file_name: File to upload
        :param bucket: Bucket to upload to
        :param object_name: S3 object name. If not specified then file_name is used
        :return: True if file was uploaded, else False
        """

        # Upload the file
        file_name = os.path.basename(local_path)
        try:
            response = self.s3_client.upload_file(
                local_path, bucket, prefix + file_name
            )
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def download_files(self, bucket, s3_path, local_path):

        """Download a file from an S3 bucket

        :param bucket: Bucket to download from
        :param object_name: S3 object name. If not specified then file_name is used
        :param local_path: local path to download the file
        :return: True if file was downloaded, else False
        """

        # make sure the local path exists
        if not os.path.exists(os.path.dirname(local_path)):
            os.makedirs(os.path.dirname(local_path))

        try:
            response = self.s3_client.download_file(bucket, s3_path, local_path)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def list_files(self, bucket, prefix):
        """List all files in an S3 bucket

        :param bucket: Bucket to list
        :return: List of file names in bucket
        """

        # Retrieve the list of existing buckets
        response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        logging.debug(response)
        return response
