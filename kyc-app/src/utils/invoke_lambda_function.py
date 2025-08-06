import boto3
import json

def invoke_lambda_function(function_name, payload=None, region_name='us-east-1'):
    """
    Invokes an AWS Lambda function from an EC2 instance
    
    :param function_name: Name of the Lambda function to invoke
    :param payload: Input data for the Lambda function (dict)
    :param region_name: AWS region where the Lambda function resides
    :return: Response from the Lambda function
    """
    # Initialize a Lambda client
    lambda_client = boto3.client('lambda', region_name=region_name)
    
    # Convert payload to JSON string if provided
    if payload is not None and not isinstance(payload, str):
        payload = json.dumps(payload)
    
    try:
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=payload
        )
        
        # Read and parse the response
        response_payload = response['Payload'].read().decode('utf-8')
        return json.loads(response_payload)
        
    except Exception as e:
        print(f"Error invoking Lambda function: {e}")
        raise

if __name__ == "__main__":
    # Example usage
    lambda_function_name = "street_view"
    input_data = {
        "CLNT_NBR": "1234"
    }
    
    try:
        result = invoke_lambda_function(lambda_function_name, input_data)
        print("Lambda response:", result)
    except Exception as e:
        print("Failed to invoke Lambda:", str(e))