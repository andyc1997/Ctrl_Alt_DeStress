import boto3
import pandas as pd
from io import StringIO


# Initialize S3 client
s3 = boto3.client('s3')

def create_client_entry(clnt_nbr):
    s3 = boto3.client('s3')
    bucket_name = 'client-master-entry'
    object_key = 'clnt_master_entry.csv'

    # Download CSV from S3
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    csv_content = response['Body'].read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_content))
    bool_clnt_found = clnt_nbr in df['CLNT_NBR'].astype(str).values

    # Check if customer_id exists
    if not bool_clnt_found:
        # Append new row (customize columns as needed)
        new_row = {'CLNT_NBR': clnt_nbr, 'Proc1': 'NA', 'Proc2': 'NA', 'Proc3': 'NA', 'Proc4': 'NA', 'Score': 'NA'}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Upload updated CSV back to S3
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        s3.put_object(Bucket=bucket_name, Key=object_key, Body=csv_buffer.getvalue())

        # If the row already exists, return False    
    this_record = df[df['CLNT_NBR'].astype(str) == clnt_nbr]
    return bool_clnt_found, this_record # Row already exists

bool_clnt_found, this_record = create_client_entry('123456')
print(bool_clnt_found, this_record)