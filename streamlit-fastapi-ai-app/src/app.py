import streamlit as st
import os
import requests
import boto3
from utils.folder_manager import create_client_entry

def main():
    st.title("KYC Intelligent Agent Management")
    
    client_id = st.text_input("Enter Client ID:")
    
    if st.button("Create Folder"):
        if client_id:
            folder_created = create_client_entry(client_id)  
            if folder_created:
                st.success(f"Folder for client '{client_id}' created successfully!")
            else:
                st.error(f"Folder for client '{client_id}' already exists or could not be created.")
        else:
            st.error("Please enter a valid Client ID.")
    
    client_status = 
    
    if st.button("Run AI Agents"):
        if client_id:
            with st.spinner("Running AI agents..."):
                # Call FastAPI endpoints to trigger AI agents
                response1 = requests.post(f"http://localhost:8000/agent1/{client_id}")
                response2 = requests.post(f"http://localhost:8000/agent2/{client_id}")
                
                if response1.status_code == 200:
                    st.success("Agent 1 completed successfully!")
                else:
                    st.error("Agent 1 failed to run.")
                
                if response2.status_code == 200:
                    st.success("Agent 2 completed successfully!")
                else:
                    st.error("Agent 2 failed to run.")
        else:
            st.error("Please enter a valid Client ID.")

if __name__ == "__main__":
    main()