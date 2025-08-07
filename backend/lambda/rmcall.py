import boto3
import time
import json
import urllib.request
import re

# Initialize AWS clients
transcribe_client = boto3.client('transcribe')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')  # Adjust region as needed
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    # Configuration
    bucket_name = 'rmcallprocess'
    audio_file = 'banker_conversation_vo.mp3'
    job_name = f'transcription-job-{int(time.time())}'

    try:
        # Step 1: Start transcription job
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            LanguageCode='en-US',  # Adjust based on audio language
            MediaFormat='mp3',
            Media={
                'MediaFileUri': f's3://{bucket_name}/{audio_file}'
            },
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 2  # Assuming two speakers (banker and customer)
            }
        )

        # Wait for transcription job to complete
        while True:
            status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            print("Transcription in progress...")
            time.sleep(10)

        # Retrieve transcription results
        if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            with urllib.request.urlopen(transcript_uri) as response:
                transcript_data = json.loads(response.read().decode())
            transcript_text = transcript_data['results']['transcripts'][0]['transcript']
            print("Transcription:", transcript_text)
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Transcription failed'})
            }

        # Step 2: Extract entities with Bedrock
        prompt = f"""
Extract the customer's name, date of birth, address, occupation, and source of wealth from the following text. Return only a valid JSON object with the specified keys. If any information is missing, use "Not found" as the value. Do not include any additional text, explanations, or formatting.

Text: {transcript_text}

{{
  "customer_name": "",
  "date_of_birth": "",
  "address": "",
  "occupation": "",
  "source_of_wealth": ""
}}
"""

        # Invoke Bedrock model
        response = bedrock_client.invoke_model(
            modelId='amazon.titan-text-express-v1',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'inputText': prompt,
                'textGenerationConfig': {
                    'maxTokenCount': 1000,
                    'temperature': 0.5
                }
            })
        )

        # Parse the response with enhanced error handling
        bedrock_output = json.loads(response['body'].read().decode())
        print("Full Bedrock Response:", json.dumps(bedrock_output, indent=2))
        raw_completion = bedrock_output['results'][0]['outputText'].strip()
        print("Raw Bedrock Output:", raw_completion)
        if not raw_completion:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Bedrock returned an empty response'})
            }
        try:
            extracted_data = json.loads(raw_completion)
            print("Extracted Data:", json.dumps(extracted_data, indent=2))
        except json.JSONDecodeError as e:
            print(f"JSON Parsing Error: {e}")
            json_match = re.search(r'\{[\s\S]*\}', raw_completion)
            if json_match:
                cleaned_json = json_match.group(0)
                try:
                    extracted_data = json.loads(cleaned_json)
                    print("Extracted Data:", json.dumps(extracted_data, indent=2))
                except json.JSONDecodeError as e2:
                    print(f"Failed to parse cleaned JSON: {e2}")
                    print("Cleaned JSON attempt:", cleaned_json)
                    return {
                        'statusCode': 500,
                        'body': json.dumps({'error': 'Failed to parse Bedrock JSON output'})
                    }
            else:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': 'No valid JSON found in Bedrock response'})
                }

        # Step 3: Save extracted data to S3
        output_file = f'output/extracted_data_{job_name}.json'
        s3_client.put_object(
            Bucket=bucket_name,
            Key=output_file,
            Body=json.dumps(extracted_data, indent=2)
        )
        print(f"Extracted data saved to s3://{bucket_name}/{output_file}")

        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing complete',
                'transcription': transcript_text,
                'extracted_data': extracted_data,
                's3_output': f's3://{bucket_name}/{output_file}'
            })
        }

    except Exception as e:
        print(f"Error in Lambda execution: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
