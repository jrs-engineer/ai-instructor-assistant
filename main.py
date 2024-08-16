import streamlit as st
import pandas as pd
import numpy as np

from assistant import get_result

st.title('AI Instructor Assistant')

if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Function to handle user input
def handle_input():
    if 'result' in st.session_state:
        del st.session_state['result']
    if 'table_df' in st.session_state:
        del st.session_state['table_df']

    user_input = st.session_state['user_input']
    st.session_state['messages'].append({'role': 'user', 'content': user_input})
    res, query = get_result(user_input)
    print("result: ", res, query)
    
    st.session_state['messages'].append({'role': 'bot', 'content': f'Query: {query}'})
    st.session_state['user_input'] = ''

    if res == "ERROR":
        st.session_state['result'] = query
    elif isinstance(res, str):
        st.session_state['result'] = res
    else:
        rows, description = res
        colnames = [desc[0] for desc in description]
        df = pd.DataFrame(rows, columns=colnames)
        st.session_state['table_df'] = df

with st.sidebar:
    st.header("Chat History")
    # Display chat messages
    for message in st.session_state['messages']:
        if message['role'] == 'user':
            st.write(f"[**Instructor:**] {message['content']}")
        else:
            st.write(f"[**Assitant:**] {message['content']}")

# Input box for user to type their message
st.text_input("hidden", key='user_input', label_visibility="hidden", on_change=handle_input)

# Display the updated DataFrame
if 'table_df' in st.session_state and not st.session_state['table_df'].empty:
    st.dataframe(st.session_state['table_df'], use_container_width=True)

# Display the result
st.write(st.session_state.get('result', ''))