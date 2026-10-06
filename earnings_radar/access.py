"""Local development stays open; hosted entrypoint requires a configured password."""
import hmac
import os
import streamlit as st


def require_access():
    if os.getenv('RADAR_REQUIRE_AUTH','false').lower()!='true':return
    expected=os.getenv('RADAR_DASHBOARD_PASSWORD')
    if not expected:
        st.error('Hosted access is not configured. Set the dashboard password in hosting settings.')
        st.stop()
    if st.session_state.get('_radar_access_granted'):return
    st.title('Earnings Radar')
    st.caption('Private research dashboard')
    with st.form('radar_access'):
        entered=st.text_input('Dashboard password',type='password')
        submitted=st.form_submit_button('Open dashboard')
    if submitted:
        if hmac.compare_digest(entered.encode(),expected.encode()):
            st.session_state['_radar_access_granted']=True
            st.rerun()
        else:st.error('Incorrect password.')
    st.stop()
