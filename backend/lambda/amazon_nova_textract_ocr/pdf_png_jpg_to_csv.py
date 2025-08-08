import boto3
import csv
import json
import logging
from io import StringIO
from urllib.parse import unquote_plus

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

# Configuration
input_bucket = 'output-internal-cld'  # Input S3 bucket
output_bucket = 'processed-output-cld'  # Output S3 bucket
input_folder = 'output/'  # Input folder

def read_csv_from_s3(bucket, key):
    logger.info(f"Reading CSV from S3: bucket={bucket}, key={key}")
    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    return content

def parse_csv(content):
    csv_file = StringIO(content)
    reader = csv.reader(csv_file)
    data = [row for row in reader]
    return data

def extract_info_with_nova_pro(csv_content):
    prompt = f"""
    Analyze the following CSV content and extract the client balance, statement issue date, client name, and bank name. Return the extracted information in JSON format, with no additional text or markdown markers (e.g., ```json).

    CSV Content:
    {csv_content}

    Desired Output Format:
    {{
      "client_balance": "<ending_balance>",
      "statement_issue_date": "<date>",
      "client_name": "<name>",
      "bank_name": "<bank_name>"
    }}
    """
    
    try:
        response = bedrock_client.invoke_model(
            modelId='us.amazon.nova-pro-v1:0',
            body=json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 512,
                    "temperature": 0.5,
                    "topP": 0.9
                }
            }),
            contentType='application/json',
            accept='application/json'
        )
        
        # Parse response body
        response_body = json.loads(response['body'].read().decode('utf-8'))
        logger.info(f"Bedrock response: {json.dumps(response_body, indent=2)}")
        
        # Extract content from response
        if 'output' in response_body and 'message' in response_body['output'] and 'content' in response_body['output']['message']:
            content = response_body['output']['message']['content'][0].get('text', '')
            if content:
                # Parse the JSON content directly (prompt ensures no ```json markers)
                return json.loads(content)
            else:
                raise ValueError("Empty response text from model")
        else:
            raise ValueError(f"Unexpected Bedrock response structure: {json.dumps(response_body, indent=2)}")
            
    except Exception as e:
        logger.error(f"Error invoking Bedrock: {str(e)}")
        raise

def write_csv_to_s3(data, bucket, key):
    try:
        # Validate expected fields
        expected_fields = ['client_balance', 'statement_issue_date', 'client_name', 'bank_name']
        if not all(field in data for field in expected_fields):
            raise ValueError(f"Missing required fields in data: {json.dumps(data)}")
        
        csv_buffer = StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=expected_fields)
        writer.writeheader()
        writer.writerow(data)
        
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=csv_buffer.getvalue()
        )
        logger.info(f"Successfully wrote CSV to S3: bucket={bucket}, key={key}")
    except Exception as e:
        logger.error(f"Error writing to S3: {str(e)}")
        raise

def lambda_handler(event, context):
    try:
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            # Process only files in the output/ folder
            if not key.startswith(input_folder) or not key.endswith('.csv'):
                logger.info(f"Skipping file: {key}")
                continue
                
            # Read CSV from S3
            csv_content = read_csv_from_s3(bucket, key)
            
            # Parse CSV
            csv_data = parse_csv(csv_content)
            
            # Convert CSV data to string for Nova Pro
            csv_str = '\n'.join([','.join(row) for row in csv_data])
            
            # Extract information using Nova Pro
            extracted_info = extract_info_with_nova_pro(csv_str)
            
            # Generate output key
            output_key = key.replace('.csv', '_processed.csv')
            
            # Write new CSV to output bucket
            write_csv_to_s3(extracted_info, output_bucket, output_key)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Processed successfully')
        }
    except Exception as e:
        logger.error(f"Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
