# Narratives Summarisation - Amazon Titan Text Express v1  
This function is to summarise all the processed data from Transcribe, Textract, and Lambda functions based on   
1. customer's demographics stored in bank's data warehouse  
2. web scraped result of customer's background   
3. transcribed audio call log of customer and relationship manager's calling conversation  
4. textracted supplementary documents (i.e. payslip, investment statement, other bank statement) from customer
   
It is triggered by a button event in streamlit user-interface.  

**Lambda Function URL**: <https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/deepseek-json-bedrock?tab=code>

**Parameters**:  
   * event : dict, input data from the event  
   * context : dict, context information about the Lambda function execution environment  
      * **Parameters for event json**:   
      * INPUT_TEXT : string, a consolidated result from textract, transcribe, web-scraping, street-view extraction, and internal database
          
**Return**:  
   * statusCode : integer, status code  
   * narratives : string, narratives result  

## Sample  
**Event json**
```
{
    "INPUT_TEXT" : "{'CU Number':{'4':123456704},'Name':{'4':'Jamie Dimon'},'Age':{'4':68},'Position':{'4':'CEO'}"
}
```


