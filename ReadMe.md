# 2025 Citi x AWS Hackathon - KYC & Source of Wealth (SOW) Verification Workflow
*Automated Client Due Diligence Application*
![work flow](./architectural_design.png)

## 1. Overview
This system automates **KYC (Know Your Customer)** and **Source of Wealth (SOW)** verification by:
- Gathering client data from internal and external sources
- Using AI (Amazon Bedrock, Textract, Transcribe) to analyze documents and calls
- Generating a consolidated **SOW report** for KYC checkers

## 2. Backend Workflow

### Trigger
**Step B1-2:** System detects a **KYC alert** (periodic scan or new client onboarding) and generates a **KYC list** in the database.

### Data Retrieval
**Step B3:** Fetches **client PII** (Personally Identifiable Information) from the internal database.

### External Verification (Parallel Steps)
**Step B4.1:** Triggers **Google StreetView** to capture images of the client's workplace.  
* **Lambda Function URL**: <https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/street_view?tab=code>
* Event json
```
  {  
   "CLNT_NBR" : "123456704",  
   "ADDRESS" : "270 Park Avenue,. New York City. ,. United States"  
  }
```
* Return  
<img src="./backend/lambda/google_street_view/gsv_0.jpg" width="250" height="250" />

**Step B4.2:** Runs **web scraping** to collect public data (occupation, salary, location, etc.).
* **Lambda Function URL**: <https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/externaldataprocesscode?tab=code>
* Event json
```
  {
   "CLNT_NBR" : "123456704",
   "CUSTOMER_NAME" : "Jamie Dimon",
   "OCCUPATION" : "CEO",
   "COMPANY" : "JPMorgan Chase & Co.",
   "LOCATION" : "270 Park Avenue,. New York City. ,. United States"
  }
```
### Additional Data Collection
**Step B5-7:**
- Sends an **automated email** to the Relationship Manager (RM) if extra data is needed
- RM **calls the client** and call logs are retrieved from the internal recording system

### AI Processing (Parallel Steps)
**Step B8.1:** Call recording is processed by **Amazon Transcribe** with amazon.titan-text-express-v1 to generate subtitles.  
**Step B8.2:** RM uploads **client-submitted documents**.  
**Step B8.3:** Documents are processed by **Textract (OCR)** then **Bedrock** (AI keyword analysis via amazon.titan-text-express-v1).

### Consolidation & Output
**Step B9:**
- Bedrock **analyzes corroboration level** across all data sources with amazon.titan-text-express-v1
- Generates a **final SOW form**

**Step B10:** KYC checker reviews and the **process is complete**.

## 3. Frontend (UI) Workflow

### Case Creation
**Step F0:** User inputs **Client ID** (e.g., `123456704`) to create a new case.

### Case Verification
**Step F1:** Clicks **"Check Client ID"** to confirm case exists. If not, returns to Step F0.

### Data Processing
**Step F2:** Clicks **"Run Data Processing"** to display client data in a table.

### External Agents (Parallel Steps)
**Step F3:** Clicks **"Run StreetView Agent"** to trigger Google StreetView.  
**Step F4:** Clicks **"Run Webscraping Agent"** to trigger web scraping.

### Document Upload (Optional)
**Step F5:** User uploads **supporting documents**.

### Completion
**Step F6:** Downloads **SOW form** and KYC checker takes over.

## 4. Key Features
- **Parallel Processing:** Steps B4.1/B4.2 and B8.1/B8.2/B8.3 run simultaneously
- **AI Integration:** Amazon Bedrock (Nova), Textract, Transcribe
- **Audit Trail:** Call logs, automated emails, and document tracking
