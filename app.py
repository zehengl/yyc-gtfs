import urllib.request
from pathlib import Path

import folium
import gtfs_kit as gk
import streamlit as st
from shapely.geometry import mapping
from streamlit_folium import st_folium

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


@st.cache
def load_feed(path):
    feed = gk.read_feed(path, dist_units="km")
    return feed


feed = load_feed(path)

if st.secrets.get("describe"):
    st.subheader("Stats")
    with st.spinner(f"loading {filename}..."):
        st.dataframe(feed.describe(), use_container_width=True)


if st.secrets.get("validate"):
    st.subheader("Validation")
    with st.spinner(f"validating {filename}..."):
        st.dataframe(feed.validate(), use_container_width=True)

st.subheader("Stops")
m = feed.map_stops(feed.get_stops()["stop_id"])
st_folium(m)

st.subheader("Routes")
geometrize_routes = feed.geometrize_routes()
duplicated = geometrize_routes["route_short_name"].duplicated()
geometrize_routes = geometrize_routes[~duplicated]
selected_routes = st.multiselect(
    "Choose routes",
    [
        f"{d} {n}"
        for d, n in zip(
            geometrize_routes["route_short_name"].tolist(),
            geometrize_routes["route_long_name"].tolist(),
        )
    ],
)
if selected_routes:
    # feed.map_routes() does not seem to work with streamlit
    routes = geometrize_routes[
        geometrize_routes["route_short_name"].isin(
            [l.split()[0] for l in selected_routes]
        )
    ]
    m = folium.Map((51.0447, -114.0719))
    colors = gk.COLORS_SET2
    color_ind = 0
    size = len(colors)
    for geometry in routes["geometry"]:
        coords = mapping(geometry)["coordinates"]
        try:
            folium.PolyLine(
                [(b, a) for a, b in coords], color=colors[color_ind % size]
            ).add_to(m)
        except ValueError:
            for _coords in coords:
                folium.PolyLine(
                    [(b, a) for a, b in _coords], color=colors[color_ind % size]
                ).add_to(m)
        finally:
            color_ind += 1
    st_folium(m)
