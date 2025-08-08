import streamlit as st
import pandas as pd
import boto3
import json
import time 
import streamlit.components.v1 as components

from io import StringIO
from utils.folder_manager import create_client_entry, check_client_entry, get_client_entry
from utils.invoke_lambda_function import invoke_lambda_function
from utils.invoke_s3 import s3_read_csv, s3_write_csv, s3_file_exists, s3_read_json


def main():
    st.title("KYC Intelligent Agent Management")

    # Get client ID from user input
    client_id = st.text_input("Enter Client ID:")
    s3 = boto3.client('s3')

    # Get entry details
    entry_bucket_name = 'client-master-entry'
    entry_object_key = 'clnt_master_entry.csv'

    # Initialize session state variables
    if 'client_entry' not in st.session_state:
        st.session_state.client_entry = None 
    if 'df_clnt_info' not in st.session_state:
        st.session_state.df_clnt_info = None
    if 'df_entry_table' not in st.session_state:
        st.session_state.df_entry_table = None
    else: 
        st.session_state.df_entry_table = s3_read_csv(s3, entry_bucket_name, entry_object_key)
        try:
            st.session_state.client_entry = get_client_entry(st.session_state.df_entry_table, str(client_id)).iloc[0].to_dict()
        except: 
            st.session_state.client_entry = None 
    # Create New Case
    # if st.button("Create New Case"):
    #     if client_id and len(str(client_id)) == 9:
    #         is_new_case, client_entry = create_client_entry(str(client_id), entry_bucket_name, entry_object_key)  
    #         if is_new_case:
    #             st.success(f"New case for client '{client_id}' created successfully!")
    #         else:
    #             st.info(f"New case for client '{client_id}' already exists or could not be created.")
    #         st.session_state.client_entry = client_entry.iloc[0].to_dict()
    #         st.dataframe(client_entry)
    #     else:
    #         st.info("Please enter a valid Client ID.")
    
    # Check if client entry exists 
    if st.button("Check Client ID"):
        if client_id and len(str(client_id)) == 9:
            is_new_case, client_entry = check_client_entry(str(client_id), entry_bucket_name, entry_object_key)
            if is_new_case:
                st.info(f"The client for '{client_id}' does not exist.")
                _, st.session_state.client_entry = create_client_entry(str(client_id), entry_bucket_name, entry_object_key) 
                st.success(f"New case for client '{client_id}' created successfully!")
            else:
                st.success(f"The client for '{client_id}' exists.")
                st.session_state.client_entry = client_entry.iloc[0].to_dict()
                st.dataframe(client_entry) # Display client entry details
        else:
            st.info("Please enter a valid Client ID.")
    
    # Read internal database
    if st.button("Run Data Processing"):
        if client_id:
            with st.spinner("Running Data Processing..."):
                internal_data_bucket = "internaldataprocess"
                internal_data_object = "real_cu_list.csv"
                df = s3_read_csv(s3, internal_data_bucket, internal_data_object, skiprows=10)
                df_clnt_info = get_client_entry(df, str(client_id), 'CU Number')
            st.session_state.df_clnt_info = df_clnt_info.iloc[0].to_dict()

            st.dataframe(df_clnt_info)                
        else:
            st.info("This client ID does not exist. Please create a new case first.")

    # Run Webscraping agent
    if st.button("Run Webscraping Agent"):
        st.session_state.df_entry_table = s3_read_csv(s3, entry_bucket_name, entry_object_key)
        if pd.isna(st.session_state.client_entry['Proc2']):
            with st.spinner("Running AI agents..."):
                payload = {
                        "CLNT_NBR" : st.session_state.df_clnt_info['CU Number'],
                        "CUSTOMER_NAME" : st.session_state.df_clnt_info['Name'],
                        "OCCUPATION" : st.session_state.df_clnt_info['Position'],
                        "COMPANY" : st.session_state.df_clnt_info['Employer'],
                        "LOCATION" : st.session_state.df_clnt_info['Employer Address']
                    }
                response = invoke_lambda_function("externaldataprocesscode", payload=payload)

                if response['statusCode'] == 200:
                    external_data_bucket = response['bucket']
                    external_data_object = response['s3_key']

                    st.success("Webscraping Agent completed successfully!")

                    cu_pointer = st.session_state.df_entry_table['CLNT_NBR'].astype(str) == str(client_id)
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc2'] = 'Completed'
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc2_Bucket'] = external_data_bucket
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc2_Object'] = external_data_object
                    s3_write_csv(s3, st.session_state.df_entry_table, entry_bucket_name, entry_object_key)

                    # response = s3.get_object(Bucket=external_data_bucket, Key=external_data_object)
                    # json_bytes = response['Body'].read()
                    # st.download_button(
                    #     label="Download Webscraping Data",
                    #     data=json_bytes,
                    #     file_name=external_data_object,
                    #     mime='application/json'
                    # )

                else:
                    st.error("Webscraping Agent failed to run.")
        else:
            # external_data_bucket = st.session_state.client_entry['Proc2_Bucket']
            # external_data_object = st.session_state.client_entry['Proc2_Object']
            st.info(f"This client has already been processed by the Webscraping Agent.")
            # external_data = s3_read_json(s3, external_data_bucket, external_data_object)
            # st.download_button(
            #             label=">> Download Extracted Data",
            #             data=json.dumps(external_data),
            #             file_name=external_data_object,
            #             mime="application/json"
            #         )

    # Run StreetView agent
    if st.button("Run StreetView Agent"):
        st.session_state.df_entry_table = s3_read_csv(s3, entry_bucket_name, entry_object_key)
        if pd.isna(st.session_state.client_entry['Proc1']):
            with st.spinner("Running AI agents..."):
                payload = {
                    'CLNT_NBR': st.session_state.df_clnt_info['CU Number'], 
                    'ADDRESS': st.session_state.df_clnt_info['Employer Address']
                }
                response = invoke_lambda_function("street_view", payload=payload)
                if response['statusCode'] == 200:
                    # get response
                    streetview_bucket = response['bucket']
                    streetview_object = response['image_name']
                    st.success("StreetView Agent completed successfully!")

                    # update entry table 
                    cu_pointer = st.session_state.df_entry_table['CLNT_NBR'].astype(str) == str(client_id)
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc1'] = 'Completed'
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc1_Bucket'] = streetview_bucket
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc1_Object'] = streetview_object
                    s3_write_csv(s3, st.session_state.df_entry_table, entry_bucket_name, entry_object_key)
                    
                    # display image
                    response = s3.get_object(Bucket=streetview_bucket, Key=streetview_object)
                    image_bytes = response['Body'].read()
                    st.image(image_bytes, width=200)
                else:
                    st.info("StreetView Agent failed to run. Please try again later.")
        else:
            streetview_bucket = st.session_state.client_entry['Proc1_Bucket']
            streetview_object = st.session_state.client_entry['Proc1_Object']

            response = s3.get_object(Bucket=streetview_bucket, Key=streetview_object)
            image_bytes = response['Body'].read()

            st.info("This client has already been processed by the StreetView Agent.")
            st.image(image_bytes, width=200)    

    if 'show_textract_uploader' not in st.session_state:
        st.session_state.show_textract_uploader = False

    if 'show_voice_to_text' not in st.session_state:
        st.session_state.show_voice_to_text = False

    if st.button("Run Textract Agent"):
        st.session_state.show_textract_uploader = True
        st.session_state.show_voice_to_text = False

    if st.session_state.show_textract_uploader:
        st.session_state.df_entry_table = s3_read_csv(s3, entry_bucket_name, entry_object_key)
        if pd.isna(st.session_state.client_entry['Proc3']):
            uploaded_files = st.file_uploader("Choose a file to upload", accept_multiple_files=True)
            output_keys = ''
            for i, uploaded_file in enumerate(uploaded_files):
                if uploaded_file is not None:
                    # Read file bytes
                    file_bytes = uploaded_file.read()
                    # Define S3 bucket and object key (filename)
                    upload_bucket = "doc-input-external"
                    upload_key = uploaded_file.name
                    output_bucket = "output-internal-cld"

                    # Upload to S3
                    s3.put_object(Bucket=upload_bucket, Key=upload_key, Body=file_bytes)
                    st.success(f"File '{uploaded_file.name}' uploaded to S3 bucket '{upload_bucket}'.")

                    # Give it some buffer time and only show download button if the file is processed
                    output_key = "output/filtered_" + uploaded_file.name.split('.')[0] + ".csv"
                    with st.spinner("Running AI agents for document " + str(i+1)):
                        time.sleep(30)
                    
                    # Anyway, Textract should always extract something, let write it to the entry table and wait for its completion
                    cu_pointer = st.session_state.df_entry_table['CLNT_NBR'].astype(str) == str(client_id)
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc3'] = 'Completed'
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc3_Bucket'] = output_bucket
                    output_keys = output_keys + ';' + output_key
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc3_Object'] = output_keys
                    s3_write_csv(s3, st.session_state.df_entry_table, entry_bucket_name, entry_object_key)
            if output_keys != '':
                st.success("Textract Agent completed successfully! The following files are processed: " + output_keys)

        else:
            output_bucket = st.session_state.client_entry['Proc3_Bucket']
            output_keys = st.session_state.client_entry['Proc3_Object']
            st.info(f"This client has already been processed by the Textract Agent.")
            if not pd.isna(output_keys):
                st.info("The following files have been processed: " + output_keys)

    # Run Transcribe agent
    if st.button("Run Voice-to-text Agent"):
        st.session_state.show_textract_uploader = False
        st.session_state.show_voice_to_text = True

    if st.session_state.show_voice_to_text:
        audio_file = 'banker_conversation_vo.mp3' # audio file should be automatically generated from source system. For demo, we use a static file.
        st.info(f"The following audio file is found and will be transcribed to text: {audio_file}")
        st.session_state.df_entry_table = s3_read_csv(s3, entry_bucket_name, entry_object_key)

        if pd.isna(st.session_state.client_entry['Proc4']):
            with st.spinner("Running AI agents..."):
                response = invoke_lambda_function("rmcall", payload={'mp3': audio_file})
                if response['statusCode'] == 200:
                    # get response
                    transcribe_bucket = response['body']['bucket']
                    transcribe_object = response['body']['s3_key']
                    st.success("Voice-to-text completed successfully!")

                    # update entry table 
                    cu_pointer = st.session_state.df_entry_table['CLNT_NBR'].astype(str) == str(client_id)
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc4'] = 'Completed'
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc4_Bucket'] = transcribe_bucket
                    st.session_state.df_entry_table.loc[cu_pointer, 'Proc4_Object'] = transcribe_object
                    s3_write_csv(s3, st.session_state.df_entry_table, entry_bucket_name, entry_object_key)
                    
                    # display json
                    response = s3.get_object(Bucket=transcribe_bucket, Key=transcribe_object)
                    dict_from_json = json.load(response['Body'])
                    st.success("Voice-to-Text Agent completed successfully! Message preview: " + str(dict_from_json))
                else:
                    st.info("Voice-to-Text Agent failed to run. Please try again later.")
        else:
            transcribe_bucket = st.session_state.client_entry['Proc4_Bucket']
            transcribe_object = st.session_state.client_entry['Proc4_Object']

            response = s3.get_object(Bucket=transcribe_bucket, Key=transcribe_object)
            dict_from_json = json.load(response['Body'])
            st.success("Voice-to-Text Agent completed successfully! Message preview: " + str(dict_from_json))

    if st.button("Run SOW Report"): 
        st.session_state.df_entry_table = s3_read_csv(s3, entry_bucket_name, entry_object_key)
        # textract csv ouputs
        # bucket: output-internal-cld
        # file name: filtered_Basic_Pay_stub_singledpage.csv
        cu_pointer = st.session_state.df_entry_table['CLNT_NBR'].astype(str) == str(client_id)
        df_textract = s3_read_csv(s3, st.session_state.client_entry['Proc3_Bucket'],
                                  st.session_state.client_entry['Proc3_Object'].split(';')[1])
        df_textract2 = s3_read_csv(s3, st.session_state.client_entry['Proc3_Bucket'],
                                  st.session_state.client_entry['Proc3_Object'].split(';')[2])
        json_textract = df_textract.to_json()
        json_textract2 = df_textract2.to_json()

        # citi internal database csv
        internal_data_bucket = "internaldataprocess"
        internal_data_object = "real_cu_list.csv"
        df = s3_read_csv(s3, internal_data_bucket, internal_data_object, skiprows=10)
        df_clnt_info = get_client_entry(df, str(client_id), 'CU Number').to_json()

        # transcribe json outputs
        # bucket: rmcallprocess/output/
        # file name: extracted_data_transcription-job-1754614054.json
        transcribe_bucket = st.session_state.client_entry['Proc4_Bucket']
        transcribe_object = st.session_state.client_entry['Proc4_Object']
        response_transcribe = s3.get_object(Bucket=transcribe_bucket,  Key=transcribe_object)
        json_transcribe = json.load(response_transcribe['Body'])
        transcribe_txt = json.dumps(json_transcribe)

        # webscrape json outputs
        # bucket: externaldataprocess/suggestions/
        # file name: Jamie Dimon_1754539676.json
        external_data_bucket = st.session_state.client_entry['Proc2_Bucket']
        external_data_object = st.session_state.client_entry['Proc2_Object']
        external_data = s3_read_json(s3, external_data_bucket, external_data_object)
        webscrape_txt = json.dumps(external_data)

        input_narratives = (df_clnt_info + webscrape_txt + json_textract + json_textract2 + transcribe_txt).strip(' ').replace('"', "'")
        print(input_narratives)
        df_consol = None 
        sow_report = None 
        with st.spinner("Running AI agents..."):
            response = invoke_lambda_function("deepseek-json-bedrock", payload={'INPUT_TEXT': input_narratives})
            df_consol = s3_read_csv(s3, 'sowreport', 'sow_data.csv')
            sow_report = invoke_lambda_function("sowreport", payload={})

        if sow_report['statusCode'] == 200:
            response = s3.get_object(Bucket="sowreport", Key="reports/kyc_report_1.html")
            html_content = response['Body'].read().decode('utf-8')
            components.html(html_content, height=800, scrolling=True)

            # st.download_button(
            #              label=">> Download Extracted Data",
            #              data=json.dumps(external_data),
            #              file_name=external_data_object,
            #              mime="application/json"
            #          )
        

        

            


    

if __name__ == "__main__":
    main()