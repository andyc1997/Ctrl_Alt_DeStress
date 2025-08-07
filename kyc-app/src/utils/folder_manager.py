import boto3
import pandas as pd

from invoke_s3 import s3_read_csv, s3_write_csv
from io import StringIO

# Entry schema
entry_schema = {'CLNT_NBR': None, 
                'Proc1': None, 'Proc1_Bucket': None, 'Proc1_Object': None,
                'Proc2': None, 'Proc2_Bucket': None, 'Proc2_Object': None,
                'Proc3': None, 'Proc3_Bucket': None, 'Proc3_Object': None,
                'Proc4': None, 'Proc4_Bucket': None, 'Proc4_Object': None,
                'Score': None}

def get_client_entry(df: pd.DataFrame, clnt_nbr: str, column: str='CLNT_NBR') -> pd.DataFrame:
    return df[df[column].astype(str) == clnt_nbr]

# Function to create a new client entry
def create_client_entry(clnt_nbr: str, bucket_name: str, object_key: str) -> tuple:
    # Initialize S3 client
    s3 = boto3.client('s3')
    df = s3_read_csv(s3, bucket_name, object_key)

    # Check if customer_id already exists
    is_new_case = clnt_nbr not in df['CLNT_NBR'].astype(str).values

    # Check if customer_id exists
    if is_new_case:
        # Append new row (customize columns as needed)
        new_row = entry_schema.copy()
        new_row['CLNT_NBR'] = clnt_nbr
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        s3_write_csv(s3, df, bucket_name, object_key)  # Upload updated CSV back to S3

    # Filter the DataFrame for the specific client number
    client_entry = get_client_entry(df, clnt_nbr)
    return is_new_case, client_entry

# Function to check if a client entry exists
def check_client_entry(clnt_nbr: str, bucket_name: str, object_key: str) -> tuple:
    # Initialize S3 client
    s3 = boto3.client('s3')
    df = s3_read_csv(s3, bucket_name, object_key)

    # Check if customer_id already exists
    is_new_case = clnt_nbr not in df['CLNT_NBR'].astype(str).values

    # Check if customer_id exists
    client_entry = get_client_entry(df, clnt_nbr)
    return is_new_case, client_entry

# Example usage
if __name__ == "__main__":
    bool_clnt_found, this_record = create_client_entry('123456')
    print(bool_clnt_found, this_record)