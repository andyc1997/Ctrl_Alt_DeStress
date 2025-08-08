import pandas as pd
import json

CLNT_NBR = '123456704'

# textract csv ouputs
# bucket: output-internal-cld
# file name: filtered_Basic_Pay_stub_singledpage.csv
df_textract = pd.read_csv("/content/filtered_Basic_Pay_stub_singledpage.csv")
json_textract = df_textract.to_json()

# citi internal database csv
# bucket: internaldataprocess
# file name: real_cu_list.csv
df_internal_database = pd.read_csv("/content/real_cu_list.csv", skiprows=10)
df_internal_database_cu =  df_internal_database[df_internal_database['CU Number'].astype(str) == CLNT_NBR]
json_internal_database_cu = df_internal_database_cu.to_json()

# transcribe json outputs
# bucket: rmcallprocess/output/
# file name: extracted_data_transcription-job-1754614054.json
with open("/content/extracted_data_transcription-job-1754614054.json") as json_transcribe_file:
  json_transcribe = json.load(json_transcribe_file)
  transcribe_txt = json.dumps(json_transcribe)

# webscrape json outputs
# bucket: externaldataprocess/suggestions/
# file name: Jamie Dimon_1754539676.json
with open("/content/Jamie Dimon_1754539676.json") as json_webscrape_file:
  json_webscrape = json.load(json_webscrape_file)
  webscrape_txt = json.dumps(json_webscrape)

input_narratives = (json_internal_database_cu + webscrape_txt + json_textract + transcribe_txt).strip(' ').replace('"', "'")
print(input_narratives)

# event json for aws titan narratives generation
# bucket: deepseek-json-bedrock
# file name: lambda-function.py
# {
#   "INPUT_TEXT":f"{input_narratives}"
# }
