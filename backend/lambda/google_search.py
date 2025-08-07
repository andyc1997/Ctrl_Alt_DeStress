'''
Environment Variables / Parameters:
    ADD_SRC_S3_BUCKET : string, S3 bucket for database of customer data
    GM_API_KEY : string, Personal Google Geocoding API
    IMAGE_S3_BUCKET : string, S3 bucket for storing the street view image
    SRC_FILE_NAME : string, S3 bucket for file name of customer data ADD_SRC_S3_BUCKET

Parameters:
    event : dict, input data from the event
    context : dict, context information about the Lambda function execution environment
    
    Paramters for event json:
    CLNT_NBR : string, a customer number
    CUSTOMER_NAME : string, customer name
    OCCUPATION : string, customer's occupation
    LOCATION : string, customer's company location

Returns:
    statusCode : integer, status code
    body : string, result statement
    customer_name : string, customer_name,
    url_statements : string, url_statements,google-search-credentials
    bucket : string, bucket_name
    s3_key : .json, a .json of scraped content
'''

from botocore.exceptions import ClientError
from bs4 import BeautifulSoup
import json
import boto3
import logging
import time
import re
import urllib.parse
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def scrape_statement(url, customer_name):
    """Scrape one statement containing customer_name from the given URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        customer_name_lower = customer_name.lower()
        for element in soup.find_all(['p', 'div', 'span', 'article']):
            text = element.get_text(strip=True)
            if customer_name_lower in text.lower():
                sentences = re.split(r'[.!?]+', text)
                for sentence in sentences:
                    if customer_name_lower in sentence.lower():
                        return sentence.strip()[:200]
        return "No relevant statement found"
    except Exception as e:
        logger.error(f"Failed to scrape {url}: {str(e)}")
        return f"Error scraping URL: {str(e)}"

def check_s3_access(s3_client, bucket_name):
    """Check if the S3 bucket is accessible."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"S3 bucket {bucket_name} is accessible")
        return True
    except ClientError as e:
        logger.error(f"Failed to access S3 bucket {bucket_name}: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
        return False

def get_google_search_results(customer_name, employer, location, occupation, api_key, cse_id, max_results=10):
    """Fetch up to max_results Google Search results with retry logic and fallback queries."""
    base_query = f"{customer_name} {employer}"
    secondary_query = f"{location} {occupation}"
    fallback_query = customer_name
    queries = [base_query, f"{base_query} {secondary_query}", fallback_query]
    results = []

    for query in queries:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cse_id}&q={urllib.parse.quote(query)}&num={max_results}"
                logger.info(f"Attempting search with query: {query}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                items = data.get('items', [])
                if not items:
                    logger.warning(f"No results for query: {query}")
                    continue
                
                for item in items[:max_results]:
                    url = item.get('link', '')
                    title = item.get('title', '')
                    snippet = item.get('snippet', '')
                    results.append({
                        'url': url,
                        'title': title,
                        'snippet': snippet
                    })
                if results:
                    logger.info(f"Found {len(results)} results for query: {query}")
                    return results[:max_results]
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Rate limit hit for query: {query}, attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        break
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"HTTP error for query {query}: {str(e)}")
                    break
            except Exception as e:
                logger.error(f"Failed to fetch results for query {query}, attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    break
                time.sleep(2 ** attempt)
    logger.error("All queries returned 0 results")
    return []

def validate_credentials(api_key, cse_id):
    """Validate Google API credentials with a test request."""
    try:
        test_query = "test"
        url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cse_id}&q={urllib.parse.quote(test_query)}&num=1"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logger.info("Google API credentials validated successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to validate Google API credentials: {str(e)}")
        return False

def select_top_urls_with_bedrock(search_results, customer_name, employer, location, occupation):
    """Use Bedrock (Amazon Titan) to select top 5 URLs based on prioritization rules."""
    try:
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        prompt = f"""
You are a KYC analyst selecting the top 5 most relevant URLs for due diligence on {customer_name}, employed by {employer} in {location} ({occupation} occupation). 
Prioritize URLs in this order:
1. Employer Website: Direct profiles or mentions on {employer}'s website.
2. News Source: Reputable news outlets (e.g., Forbes, Reuters, NYTimes).
3. Financial Statements: Audited by well-known firms (e.g., PwC, Deloitte).
4. Professional License or Certification: From reputable government or associations (e.g., ACAMS, AICPA).
5. Formation Documentation: Filed with government, identifying {customer_name}'s role.
6. Employer Verification Letter: With independent callback.
7. External Due Diligence Report: From firms like Kroll, CSIS, LexisNexis.

Input URLs:
{json.dumps(search_results, indent=2)}

Output a JSON list of the top 5 URLs with their assigned type, description, and priority score (1-7, 1 highest). Use the snippet and title to determine relevance.
Example output:
[
    {{"url": "https://example.com", "type": "Employer Website", "description": "Profile on employer's site", "priority_score": 1}},
    ...
]
"""
        response = bedrock_client.invoke_model(
            modelId='amazon.titan-text-express-v1',
            body=json.dumps({
                'inputText': prompt,
                'textGenerationConfig': {
                    'maxTokenCount': 1000,
                    'temperature': 0.5,
                    'topP': 0.9
                }
            }),
            contentType='application/json'
        )
        result = json.loads(response['body'].read().decode('utf-8'))
        output_text = result['results'][0]['outputText']

        # Extract JSON from the output (Titan may wrap JSON in markdown or text)
        try:
            top_urls = json.loads(output_text)
        except json.JSONDecodeError:
            # Attempt to extract JSON from potential markdown or text wrapping
            json_match = re.search(r'\[.*\]', output_text, re.DOTALL)
            if json_match:
                top_urls = json.loads(json_match.group(0))
            else:
                raise ValueError("Failed to parse JSON from Titan output")
        return top_urls[:5]
    except Exception as e:
        logger.error(f"Bedrock error: {str(e)}")
        # Fallback to rule-based selection
        return rule_based_url_selection(search_results, customer_name, employer)

def rule_based_url_selection(search_results, customer_name, employer):
    """Fallback to select top 5 URLs based on prioritization rules."""
    prioritized_urls = []
    for item in search_results:
        url = item['url'].lower()
        title = item['title'].lower()
        snippet = item['snippet'].lower()
        if employer.lower() in url or employer.lower() in title:
            url_type = 'Employer Website'
            priority_score = 1
            description = f"Profile or information about {customer_name} on {employer}'s website."
        elif any(domain in url for domain in ['forbes.com', 'reuters.com', 'nytimes.com', 'bbc.com', 'wsj.com']):
            url_type = 'News Source'
            priority_score = 2
            description = f"News article about {customer_name} or {employer}."
        elif any(keyword in title or keyword in snippet for keyword in ['financial statement', 'annual report', '10-k', 'pwc', 'deloitte']):
            url_type = 'Financial Statements'
            priority_score = 3
            description = f"Financial statements for {employer}."
        elif any(keyword in title or keyword in snippet for keyword in ['license', 'certification', 'acams', 'aicpa']):
            url_type = 'Professional License or Certification'
            priority_score = 4
            description = f"Professional license or certification for {customer_name}."
        elif 'opencorporates.com' in url:
            url_type = 'Formation Documentation'
            priority_score = 5
            description = f"Company records for {employer}."
        elif any(keyword in title or keyword in snippet for keyword in ['verification letter', 'employment verification']):
            url_type = 'Employer Verification Letter'
            priority_score = 6
            description = f"Employment verification for {customer_name}."
        elif any(keyword in title or keyword in snippet for keyword in ['kroll', 'csis', 'lexisnexis']):
            url_type = 'External Due Diligence Report'
            priority_score = 7
            description = f"Due diligence report for {customer_name} or {employer}."
        else:
            url_type = 'News Source'
            priority_score = 2
            description = f"Information related to {customer_name} or {employer}."
        prioritized_urls.append({
            'url': item['url'],
            'type': url_type,
            'description': description,
            'priority_score': priority_score
        })
    # Sort by priority_score and take top 5
    prioritized_urls.sort(key=lambda x: x['priority_score'])
    return prioritized_urls[:5]

def lambda_handler(event, context):
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')

        # Initialize bucket name
        bucket_name = os.environ.get("FUNC_S3_BUCKET")
        # add_src_bucket_name = os.environ.get("ADD_SRC_S3_BUCKET")
        # src_file = os.environ.get("SRC_FILE_NAME")

        # Check S3 access
        if not check_s3_access(s3_client, bucket_name):
            return {
                'statusCode': 500,
                'body': json.dumps({f"Cannot access S3 bucket {bucket_name}")
            }

        # Get customer number from event json input
        cu = str(event['CLNT_NBR']).strip()
        customer_name = str(event['CUSTOMER_NAME']).strip()
        occupation = str(event['OCCUPATION']).strip()
        location = str(event['LOCATION']).strip()

        # Extract customer data from event
        # response = s3.get_object(Bucket=add_src_bucket_name, Key=src_file)
        # file_content = response['Body'].read().decode('utf-8')
        # csv_reader = csv.reader(io.StringIO(file_content))
        # for row in csv_reader:
        #     if row[0] == cu:
        #         location = str(row[13]).strip()
        #         customer_name = str(row[1]).strip()
        #         employer = str(row[4]).strip()
                # industry changed to occupation / job position
                # occupation = str(row[3]).strip() 
                # break
        # customer_name = event.get('customer_name', '').strip()
        # employer = event.get('employer', '').strip()
        # location = event.get('location', '').strip()
        # occupation = event.get('occupation', '').strip()
        
        if not all([customer_name, employer, location, occupation]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required fields: customer_name, employer, location, occupation'})
            }

        # URL-encode customer_name, employer, and occupation for fallback
        encoded_customer_name = urllib.parse.quote(customer_name)
        encoded_employer = urllib.parse.quote(employer)
        encoded_occupation = urllib.parse.quote(occupation)

        # Fallback URLs
        fallback_url_statements = [
            {
                'url': f"https://www.reuters.com/search/news?blob={encoded_customer_name}",
                'description': f"News articles about {customer_name} from Reuters.",
                'type': 'News Source',
                'priority_score': 2,
                'statement': scrape_statement(f"https://www.reuters.com/search/news?blob={encoded_customer_name}", customer_name)
            },
            {
                'url': f"https://www.linkedin.com/search/results/people/?keywords={encoded_customer_name}",
                'description': f"Professional profile search for {customer_name} on LinkedIn.",
                'type': 'Employer Website',
                'priority_score': 1,
                'statement': scrape_statement(f"https://www.linkedin.com/search/results/people/?keywords={encoded_customer_name}", customer_name)
            },
            {
                'url': f"https://opencorporates.com/companies?query={encoded_employer}",
                'description': f"Company records for {employer}.",
                'type': 'Formation Documentation',
                'priority_score': 5,
                'statement': scrape_statement(f"https://opencorporates.com/companies?query={encoded_employer}", customer_name)
            }
        ]

        # bucket_name = 'externaldataprocess'

        # Fetch Google API credentials
        secrets_client = boto3.client('secretsmanager')
        try:
            # secret = secrets_client.get_secret_value(SecretId='google-search-credentials')
            # credentials = json.loads(secret['SecretString'])
            # api_key = credentials['api_key']
            # cse_id = credentials['cse_id']

            # Extract Google API and CSE keys from evironment variables
            api_key = os.environ.get("GOOGLE_API_KEY")
            cse_id = os.environ.get("GOOGLE_CSE_ID")
            
        except ClientError as e:
            logger.error(f"Failed to retrieve Google API credentials: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
            url_statements = fallback_url_statements
        else:
            # Validate credentials
            if not validate_credentials(api_key, cse_id):
                logger.warning("Using fallback URLs due to invalid Google API credentials")
                url_statements = fallback_url_statements
            else:
                # Step 1: Fetch Google Search results
                search_results = get_google_search_results(customer_name, employer, location, occupation, api_key, cse_id)
                if not search_results:
                    logger.warning("Using fallback URLs due to empty Google Search results")
                    url_statements = fallback_url_statements
                else:
                    # Step 2: Select top 5 URLs with Bedrock
                    url_statements = select_top_urls_with_bedrock(search_results, customer_name, employer, location, occupation)
                    if not url_statements:
                        logger.warning("Bedrock returned no URLs, using rule-based selection")
                        url_statements = rule_based_url_selection(search_results, customer_name, employer)
                    # Add statements to selected URLs
                    for item in url_statements:
                        item['statement'] = scrape_statement(item['url'], customer_name)
                    # Ensure 3–5 results
                    if len(url_statements) < 3:
                        logger.warning(f"Only {len(url_statements)} URLs returned, extending with fallback")
                        url_statements.extend(fallback_url_statements[:5 - len(url_statements)])
                    url_statements = url_statements[:5]

        # Store results in S3
        s3_key = f'suggestions/{customer_name}_{int(time.time())}.json'
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps({
                    'customer_name': customer_name,
                    'employer': employer,
                    'location': location,
                    'occupation': occupation,
                    'url_statements': url_statements
                })
            )
        except ClientError as e:
            logger.error(f"Failed to write to S3: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
            return {
                'statusCode': 500,
                'body': json.dumps(f"Failed to write to S3 bucket {bucket_name}")
            }

        return {
            'statusCode': 200,
            'body': json.dumps('Finished Searching'),
            'customer_name': customer_name,
            'url_statements': url_statements,google-search-credentials
            'bucket': bucket_name,
            's3_key': s3_key
        }

    except Exception as e:
        logger.error(f"Error in website suggestion: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps("Error: Internal server error")
        }
