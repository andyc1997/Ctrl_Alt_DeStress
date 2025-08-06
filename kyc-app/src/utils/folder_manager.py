import boto3
import pandas as pd
from io import StringIO

# Entry schema
entry_schema = {'CLNT_NBR': None, 'Proc1': None, 'Proc2': None, 'Proc3': None, 'Proc4': None, 'Score': None}

# S3 bucket and object details
bucket_name = 'client-master-entry'
object_key = 'clnt_master_entry.csv'

def create_client_entry(clnt_nbr: str) -> tuple:
    # Initialize S3 client
    s3 = boto3.client('s3')

    # Download CSV from S3
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    csv_content = response['Body'].read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_content))

    # Check if customer_id already exists
    bool_clnt_found = clnt_nbr in df['CLNT_NBR'].astype(str).values

    # Check if customer_id exists
    if not bool_clnt_found:
        # Append new row (customize columns as needed)
        new_row = entry_schema.copy()
        new_row['CLNT_NBR'] = clnt_nbr
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Upload updated CSV back to S3
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        s3.put_object(Bucket=bucket_name, Key=object_key, Body=csv_buffer.getvalue())

    # Filter the DataFrame for the specific client number
    this_record = df[df['CLNT_NBR'].astype(str) == clnt_nbr]
    return bool_clnt_found, this_record

# Example usage
# bool_clnt_found, this_record = create_client_entry('123456')
# print(bool_clnt_found, this_record)