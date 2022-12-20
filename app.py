import urllib.request
from pathlib import Path

import gtfs_kit as gk
import streamlit as st

filename = "CT_GTFS.zip"
st.set_page_config(page_title="yyc-gtfs", page_icon="railway_car")
st.title("yyc-gtfs")
st.caption("A Streamlit app to visualize City of Calgary's GTFS feed")

path = Path(filename)
if path.exists():
    st.success(f"{filename} has been found from disk!")
else:
    with st.spinner(f"Downloading {filename}..."):
        urllib.request.urlretrieve(
            r"https://data.calgary.ca/download/npk7-z3bj/application%2Fx-zip-compressed",
            filename,
        )
    st.success(f"{filename} has been downloaded!")

with st.spinner(f"loading {filename}..."):
    feed = gk.read_feed(path, dist_units="km")
    st.dataframe(feed.describe(), use_container_width=True)
