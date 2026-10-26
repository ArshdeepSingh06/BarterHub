import streamlit as st

st.set_page_config(page_title="BarterHub", page_icon="🔄")

st.title("BarterHub")
st.write("Exchange useful items and skills with your community—without money.")

st.subheader("Find something you need")
st.text_input("Search listings", placeholder="Try books, tutoring, or gardening")
st.info("Listings will appear here as the project grows.")