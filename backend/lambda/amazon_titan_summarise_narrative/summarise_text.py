'''
Parameters:
    event : dict, input data from the event
    context : dict, context information about the Lambda function execution environment
    
    Parameters for event json:
    INPUT_TEXT : string, a consolidated result from textract, transcribe, web-scraping, street-view extraction, and internal database
    *sample json input : {
                            "INPUT_TEXT" : "{'CU Number':{'4':123456704},'Name':{'4':'Jamie Dimon'},'Age':{'4':68},'Position':{'4':'CEO'}"
                         }

Returns:
    statusCode : integer, status code
    narratives : string, narratives result 
'''

import boto3, json

def lambda_handler(event, context):
    try:
        input_text = str(event['INPUT_TEXT'])
        # input_text = """
        # Elon Musk is a South African-born entrepreneur and business magnate best known for his ambitious ventures in technology and innovation. After co-founding Zip2 (a web software company sold to Compaq for $307 million in 1999) and X.com (which became PayPal after a merger, later acquired by eBay for $1.5 billion), Musk shifted focus to transformative industries. In 2002, he founded SpaceX with the goal of reducing space travel costs and enabling Mars colonization, achieving milestones like reusable rockets. He joined Tesla Motors (now Tesla, Inc.) in 2004, revolutionizing electric vehicles as CEO while promoting sustainable energy. Musk has since launched Neuralink (brain-computer interfaces), The Boring Company (tunnel infrastructure), and played a key role in OpenAI's early development. His career reflects a consistent focus on disruptive technologies addressing global challenges.
        # """
        
        bedrock = boto3.client(service_name='bedrock-runtime')
        
        # Titan-validated schema with political context
        body = json.dumps({
            "inputText": f"Summarise this statement: '{input_text}'. Provide a concise summary starting with describing the customer's background. You can ignore the customer's identifiable information such as birthday, ID number, or home address.",
            "textGenerationConfig": {
                "maxTokenCount": 1000,
                "temperature": 1,
                "topP": 0.9
               
            }
        })
        
        response = bedrock.invoke_model(
            body=body,
            modelId='amazon.titan-text-express-v1',
            accept='application/json',
            contentType='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        summary = response_body['results'][0]['outputText'].strip()
        
        return {
            'statusCode': 200,
            'narratives': summary
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f"Error generating summary: {str(e)}"
        }
