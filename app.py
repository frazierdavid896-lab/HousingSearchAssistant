import streamlit as st

st.set_page_config(
    page_title="Housing Search Assistant",
    page_icon="🏠",
    layout="wide"
)

st.title("Housing Search Assistant")

st.write("### Automatic 2,000-foot Property Screening")

addresses = st.text_area(
    "Paste one address per line:",
    height=250,
    placeholder="""2421 S Oak St., Little Rock, AR
3215 Ludwig St. #B, Little Rock, AR
1608 S Cedar St., Little Rock, AR"""
)

if st.button("Screen Properties"):
    if not addresses.strip():
        st.warning("Please paste one or more addresses.")
    else:
        st.success(f"{len(addresses.splitlines())} properties received.")