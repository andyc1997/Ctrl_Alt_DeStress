import pandas as pd
import json 

from botocore.client import BaseClient
from botocore.exceptions import ClientError
from io import StringIO

def s3_write_csv(s3: BaseClient, df: pd.DataFrame, bucket_name: str, object_key: str):
    # Convert DataFrame to CSV and upload to S3
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=bucket_name, Key=object_key, Body=csv_buffer.getvalue())

def s3_read_csv(s3: BaseClient, bucket_name: str, object_key: str, skiprows = None) -> pd.DataFrame:
    # Read CSV from S3 and return as DataFrame
    csv_obj = s3.get_object(Bucket=bucket_name, Key=object_key)
    body = csv_obj['Body'].read().decode('utf-8')
    return pd.read_csv(StringIO(body), skiprows=skiprows)

def s3_read_json(s3: BaseClient, bucket_name: str, object_key: str):
    # Read json from S3 and return as DataFrame
    json_obj = s3.get_object(Bucket=bucket_name, Key=object_key)
    body = json_obj['Body'].read()
    return json.loads(body)

def s3_file_exists(s3, bucket_name, object_key):
    try:
        s3.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise