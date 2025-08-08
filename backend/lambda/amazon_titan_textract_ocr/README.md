# Textract - Amazon Titan Text Express v1  
This function is to analyse the supplementary documents (i.e. payslip, investment statement, other bank statement) from customer, summarise the data and output the result as a .csv.   
It is triggered by a button event in streamlit user-interface.  

**Lambda Function URL**: <https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/TextractToCSV?tab=code>

**Return**:  
   * statusCode : integer, status code  
   * body : string, csv outputs path in S3 bucket
   * .csv : a .csv of processed result based on png/jpg/pdf input  
