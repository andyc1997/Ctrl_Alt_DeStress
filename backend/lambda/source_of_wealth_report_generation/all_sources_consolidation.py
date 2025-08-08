import json
import boto3
import csv
from io import StringIO

def lambda_handler(event, context):
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    # Define source and target buckets
    csv_bucket = 'internaldataprocess'
    csv_key = 'real_cu_list.csv'
    json_bucket = 'externaldataprocess'
    json_key = 'suggestions/Jamie Dimon_1754642273.json'
    target_bucket = 'consolidation'
    target_key = 'output/merged_output.csv'
    
    try:
        # Read CSV file from S3
        csv_obj = s3_client.get_object(Bucket=csv_bucket, Key=csv_key)
        csv_content = csv_obj['Body'].read().decode('utf-8')
        csv_reader = csv.reader(StringIO(csv_content))
        
        # Get CSV headers and rows
        csv_headers = next(csv_reader, None)
        if not csv_headers:
            return {
                'statusCode': 400,
                'body': json.dumps('CSV file is empty or has no headers')
            }
        csv_rows = [row for row in csv_reader]
        
        # Read JSON file from S3
        json_obj = s3_client.get_object(Bucket=json_bucket, Key=json_key)
        json_content = json_obj['Body'].read().decode('utf-8')
        json_data = json.loads(json_content)
        
        # Handle JSON data (list or single record)
        if not isinstance(json_data, list):
            json_data = [json_data]
        
        # Get JSON headers from the first record (if any)
        json_headers = list(json_data[0].keys()) if json_data else []
        
        # Combine headers (avoid duplicates)
        combined_headers = csv_headers + [h for h in json_headers if h not in csv_headers]
        
        # Convert CSV rows to match combined headers
        combined_rows = []
        for row in csv_rows:
            # Pad CSV row with empty strings for JSON headers
            combined_row = row + [''] * len(json_headers)
            combined_rows.append(combined_row)
        
        # Convert JSON records to rows
        for json_record in json_data:
            # Create row with empty strings for CSV headers and JSON values
            row = [''] * len(csv_headers) + [str(json_record.get(h, '')) for h in json_headers]
            combined_rows.append(row)
        
        if not combined_rows:
            return {
                'statusCode': 404,
                'body': json.dumps('No data found in CSV or JSON')
            }
        
        # Write to CSV
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(combined_headers)  # Write headers
        csv_writer.writerows(combined_rows)  # Write data
        
        # Upload to target S3 bucket
        s3_client.put_object(
            Bucket=target_bucket,
            Key=target_key,
            Body=csv_buffer.getvalue()
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully created {target_key} in {target_bucket}')
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
