import boto3
import json

def lambda_handler(event, context):
    try:
        input_text = """
        Elon Musk is a South African-born entrepreneur and business magnate best known for his ambitious ventures in technology and innovation. After co-founding Zip2 (a web software company sold to Compaq for $307 million in 1999) and X.com (which became PayPal after a merger, later acquired by eBay for $1.5 billion), Musk shifted focus to transformative industries. In 2002, he founded SpaceX with the goal of reducing space travel costs and enabling Mars colonization, achieving milestones like reusable rockets. He joined Tesla Motors (now Tesla, Inc.) in 2004, revolutionizing electric vehicles as CEO while promoting sustainable energy. Musk has since launched Neuralink (brain-computer interfaces), The Boring Company (tunnel infrastructure), and played a key role in OpenAI's early development. His career reflects a consistent focus on disruptive technologies addressing global challenges.
        """
        
        bedrock = boto3.client(service_name='bedrock-runtime')
        
        # Titan-validated schema with political context
        body = json.dumps({
            "inputText": f"Summarize this statement: '{input_text}'. Provide a concise summary.",
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
            'body': summary
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f"Error generating summary: {str(e)}"
        }
