import boto3
import os

class CloudSync:
    def __init__(self, bucket_name, aws_access_key, aws_secret_key, region_name='us-east-1'):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region_name
        )

    def upload_file(self, file_path, s3_path):
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_path)
            return True, f"File {file_path} uploaded to {s3_path}"
        except Exception as e:
            return False, str(e)

    def download_file(self, s3_path, file_path):
        try:
            self.s3_client.download_file(self.bucket_name, s3_path, file_path)
            return True, f"File {s3_path} downloaded to {file_path}"
        except Exception as e:
            return False, str(e)

    def list_files(self, prefix=''):
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if 'Contents' in response:
                return [item['Key'] for item in response['Contents']], None
            return [], None
        except Exception as e:
            return [], str(e)