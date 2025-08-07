import boto3
import csv
import io
import json
import urllib.parse

def lambda_handler(event, context):
    # Initialize AWS clients
    textract = boto3.client('textract')
    s3 = boto3.client('s3')
    bedrock = boto3.client('bedrock-runtime')

    # Specify input and output buckets
    input_bucket = 'doc-input-external'  # Replace with your input bucket
    output_bucket = 'output-internal-cld'  # Replace with your output bucket
    document = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    raw_csv_key = f'output/raw_{document.split("/")[-1].split(".")[0]}.csv'
    filtered_csv_key = f'output/filtered_{document.split("/")[-1].split(".")[0]}.csv'

    # Extract text using Textract OCR
    response = textract.detect_document_text(
        Document={'S3Object': {'Bucket': input_bucket, 'Name': document}}
    )
    blocks = response['Blocks']

    # Process text blocks
    data = []
    for block in blocks:
        if block['BlockType'] == 'LINE':
            data.append(block.get('Text', ''))

    # Create raw CSV
    raw_output = io.StringIO()
    writer = csv.writer(raw_output)
    writer.writerow(['Extracted Text'])
    for line in data:
        writer.writerow([line])
    s3.put_object(
        Bucket=output_bucket,
        Key=raw_csv_key,
        Body=raw_output.getvalue().encode('utf-8')
    )

    # Your custom Bedrock prompt
    custom_prompt = """
    You are a KYC document specialist. Given the following text, extract only the demographic and important information (e.g. balance, address, name, statement date, etc.) and return them as a concise list. Ignore account numbers, and other non-transaction details. Format the output as a list of strings.
    text:
    {text}
    """
    # Prepare text for Bedrock
    text_input = "\n".join(data)
    prompt = custom_prompt.format(text=text_input)

    # Call Bedrock to analyze and filter
    bedrock_response = bedrock.invoke_model(
        modelId='amazon.nova-pro-v1:0',  # Nova Pro model ID
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "prompt": prompt,
            "max_new_tokens": 1000,  # Use max_new_tokens for Nova Pro
            "temperature": 0.7,
            "top_p": 0.9
        })
    )
    filtered_data = json.loads(bedrock_response['body'].read())['text']
    # Parse filtered data (assuming Bedrock returns a list of strings)
    try:
        filtered_lines = json.loads(filtered_data) if filtered_data.startswith('[') else filtered_data.split('\n')
    except:
        filtered_lines = filtered_data.split('\n')

    # Create filtered CSV
    filtered_output = io.StringIO()
    writer = csv.writer(filtered_output)
    writer.writerow(['Filtered Transaction'])
    for line in filtered_lines:
        if line.strip():
            writer.writerow([line.strip()])

    # Upload filtered CSV to S3
    s3.put_object(
        Bucket=output_bucket,
        Key=filtered_csv_key,
        Body=filtered_output.getvalue().encode('utf-8')
    )

    return {
        'statusCode': 200,
        'bucket': output_bucket,
        'object_key': filtered_csv_key
        #'body': json.dumps(f'Filtered CSV uploaded to s3://{output_bucket}/{filtered_csv_key}')
    }
