import json
import boto3
import csv
from io import StringIO
from jinja2 import Template, TemplateError
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def lambda_handler(event, context):
    # Initialize AWS S3 client
    s3_client = boto3.client('s3')
    
    # Define S3 bucket and file keys
    input_bucket = 'sowreport'
    template_key = 'sowreport_template.html'
    csv_key = 'sow_data.csv'
    output_bucket = 'sowreport'
    
    try:
        # Verify bucket exists and is accessible
        s3_client.head_bucket(Bucket=input_bucket)
        logger.info(f"Bucket '{input_bucket}' is accessible")
        
        # Check if template file exists
        try:
            s3_client.head_object(Bucket=input_bucket, Key=template_key)
            logger.info(f"Template file '{template_key}' found in bucket '{input_bucket}'")
        except s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise Exception(f"Template file '{template_key}' not found in bucket '{input_bucket}'")
            raise
        
        # Check if CSV file exists
        try:
            s3_client.head_object(Bucket=input_bucket, Key=csv_key)
            logger.info(f"CSV file '{csv_key}' found in bucket '{input_bucket}'")
        except s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise Exception(f"CSV file '{csv_key}' not found in bucket '{input_bucket}'")
            raise
        
        # Download the HTML template from S3
        template_obj = s3_client.get_object(Bucket=input_bucket, Key=template_key)
        template_data = template_obj['Body'].read().decode('utf-8')
        logger.info("Successfully downloaded HTML template")
        
        # Download the CSV file from S3
        csv_obj = s3_client.get_object(Bucket=input_bucket, Key=csv_key)
        csv_data = csv_obj['Body'].read().decode('utf-8')
        logger.info("Successfully downloaded CSV file")
        
        # Parse CSV data
        csv_file = StringIO(csv_data)
        csv_reader = csv.DictReader(csv_file)
        data_rows = [row for row in csv_reader]
        
        if not data_rows:
            logger.warning("CSV file is empty or has no data rows")
            return {
                'statusCode': 400,
                'body': json.dumps('Error: CSV file is empty or has no data rows')
            }
        
        logger.info(f"Parsed {len(data_rows)} rows from CSV with headers: {list(data_rows[0].keys())}")
        
        # Extract placeholders from template (e.g., {{field_name}})
        placeholders = set(re.findall(r'\{\{\s*(\w+)\s*\}\}', template_data))
        csv_headers = set(data_rows[0].keys())
        unmatched_placeholders = placeholders - csv_headers
        if unmatched_placeholders:
            logger.warning(f"Unmatched placeholders in template: {unmatched_placeholders}")
            # Preprocess template to replace unmatched placeholders with empty string
            for placeholder in unmatched_placeholders:
                template_data = template_data.replace(f'{{{{ {placeholder} }}}}', '')
                template_data = template_data.replace(f'{{{{{placeholder}}}}}', '')
            logger.info("Replaced unmatched placeholders with empty strings")
        
        # Log template content for debugging
        logger.info(f"Template content (first 500 chars): {template_data[:500]}")
        
        # Load the HTML template with Jinja2
        try:
            template = Template(template_data)
        except TemplateError as e:
            logger.error(f"Jinja2 template parsing error: {str(e)}")
            return {
                'statusCode': 400,
                'body': json.dumps(f"Error: Invalid template syntax - {str(e)}")
            }
        
        # Process each row in the CSV to generate an HTML report
        for index, row in enumerate(data_rows):
            logger.info(f"Processing row {index + 1} for report generation")
            
            # Render the template with CSV row data
            try:
                html_content = template.render(**row)
            except TemplateError as e:
                logger.error(f"Jinja2 rendering error for row {index + 1}: {str(e)}")
                return {
                    'statusCode': 400,
                    'body': json.dumps(f"Error: Failed to render template for row {index + 1} - {str(e)}")
                }
            
            # Convert HTML content to bytes
            html_bytes = html_content.encode('utf-8')
            
            # Generate output file key (unique for each row)
            output_key = f'reports/kyc_report_{index + 1}.html'
            
            # Upload the generated report to S3
            s3_client.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=html_bytes,
                ContentType='text/html'
            )
            logger.info(f"Uploaded report to '{output_bucket}/{output_key}'")
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully generated {len(data_rows)} KYC reports in HTML format')
        }
    
    except s3_client.exceptions.NoSuchBucket as e:
        logger.error(f"Bucket '{input_bucket}' does not exist or is inaccessible: {str(e)}")
        return {
            'statusCode': 404,
            'body': json.dumps(f"Error: Bucket '{input_bucket}' does not exist or is inaccessible")
        }
    except s3_client.exceptions.ClientError as e:
        logger.error(f"S3 error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: S3 operation failed - {str(e)}")
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }
