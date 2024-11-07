import os
import re
import sys
import pandas as pd
import streamlit as st
from typing import Any, Dict, List, Optional, Tuple
import requests
 
# Initialize Streamlit app
st.title("TaskWeaver  App")

# Change current directory to the directory of this file for loading resources
os.chdir(os.path.dirname(__file__))
 
# Add repo path to sys.path
repo_path = os.path.join(os.path.dirname(__file__), "../../")
sys.path.append(repo_path)
 
from taskweaver.app.app import TaskWeaverApp
from taskweaver.memory.attachment import AttachmentType
from taskweaver.memory.type_vars import RoleName
from taskweaver.module.event_emitter import PostEventType, RoundEventType, SessionEventHandlerBase
from taskweaver.session.session import Session
 
# Initialize TaskWeaver app
project_path = os.path.join(repo_path, "project")
app = TaskWeaverApp(app_dir=project_path, use_local_uri=True)
 
# Store session info
app_session_dict: Dict[str, Session] = {}

if 'sessions' not in st.session_state:
   st.session_state.sessions = app.get_session()

session=st.session_state.sessions
cwd_path = session.execution_cwd

def is_link_clickable(url: str):
    if url:
        try:
            response = requests.get(url)
            # If the response status code is 200, the link is clickable
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    else:
        return False

# Function to get the response from the llm model 
def get_response(user_query):
   response_round = session.send_message(user_query)
   artifact_paths = [
        p
        for p in response_round.post_list
        for a in p.attachment_list
        if a.type == AttachmentType.artifact_paths
        for p in a.content
    ]
   for post in [p for p in response_round.post_list if p.send_to == "User"]:
        files: List[Tuple[str, str]] = []
        if len(artifact_paths) > 0:
            for file_path in artifact_paths:
                # if path is image or csv (the top 5 rows), display it
                file_name = os.path.basename(file_path)
                files.append((file_name, file_path))
        
        user_msg_content = post.message
        pattern = r"(!?)\[(.*?)\]\((.*?)\)"
        matches = re.findall(pattern, user_msg_content)
        for match in matches:
            img_prefix, file_name, file_path = match
            if "://" in file_path:
                if not is_link_clickable(file_path):
                    user_msg_content = user_msg_content.replace(
                        f"{img_prefix}[{file_name}]({file_path})",
                        file_name,
                    )
                continue
            files.append((file_name, os.path.join(cwd_path,file_path)))
            user_msg_content = user_msg_content.replace(
                f"{img_prefix}[{file_name}]({file_path})",
                file_name,
            )
            # elements = file_display(files,cwd_path)   
   for val in response_round.post_list[1:]:
      yield val.message
     
#  Here we are cheking that is the list for chat is created or not and if not will create the chat list
if "chat_history" not in st.session_state:
   st.session_state.chat_history = []

# Here we are printing the chat history in this current session
for message in st.session_state.chat_history:
   if list( message.keys())[0]=="Human":
      with st.chat_message("Human",avatar="🤵"):
         st.markdown(message["Human"])
         
   elif list(message.keys())[0]=="AI":
      with st.chat_message("AI",avatar="🤖"):
         st.markdown(message["AI"]) 

def handle_file_upload(uploaded_file):
    if uploaded_file is not None:
        uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        file_path = os.path.join(uploads_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        file_name=file_path.split("/")[-1].split(".")[0]
        return file_path,file_name
    return None
  
# Here we are taking the query from the uses and taking the response from the llm model 
uploaded_file = st.file_uploader("Upload a file", type=["txt", "pdf", "docx", "csv"])
user_query=st.chat_input("Your message",key="message_input")

if "file" not in st.session_state:
    st.session_state.file =set()
    
if uploaded_file is not None:
    file_path,file_name = handle_file_upload(uploaded_file)
    query=f"Upload the file {file_name} in this path {file_path}"
    if file_name not in st.session_state.file:
        st.session_state.file.add(file_name)
        response=get_response(query)
        for response in get_response(query):
            st.markdown(response)
            st.session_state.chat_history.append({"AI":response})
        st.write(f"File uploaded successfully!")   
    else:
        st.markdown("File Already Uploaded")

    
if user_query is not None and user_query!="":
    st.session_state.chat_history.append({"Human":user_query})
    if uploaded_file is not None:
        uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    with st.chat_message("Human",avatar="🤵"):
      st.markdown(user_query)
    with st.chat_message("TaskWeaver",avatar="🤖"):
       if uploaded_file is not None:
           user_query+=f"""if loaded files exist in {uploads_dir+"/"} then take this path to load the
                    data from there and save the files and images generated in this path {cwd_path}"""
       else:
           user_query+=f"""then and save the files and images generated in this path {cwd_path}""" 
    response="Loading" 
    if user_query is not None:
        with st.spinner("Loading the responses"):
            for response in get_response(user_query):
                st.markdown(response)
                st.session_state.chat_history.append({"AI":response})      
    


         
   