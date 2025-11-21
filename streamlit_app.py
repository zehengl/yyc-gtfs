import urllib.request
from pathlib import Path

import folium
import gtfs_kit as gk
import plotly.express as px
import streamlit as st
from shapely.geometry import mapping
from streamlit_folium import st_folium

filename = "CT_GTFS.zip"
st.set_page_config(page_title="yyc-gtfs", page_icon=":oncoming_bus:")
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


@st.cache_data
def load_feed(path):
    feed = gk.read_feed(path, dist_units="km")
    return feed


@st.cache_data
def get_trip_stats(_feed):
    return _feed.compute_trip_stats()


feed = load_feed(path)

colors = gk.COLORS_SET2
color_size = len(colors)
centroid = feed.compute_centroid()
lat, lon = centroid.y, centroid.x

if st.secrets.get("describe"):
    st.subheader("Stats")
    with st.spinner(f"loading {filename}..."):
        st.dataframe(feed.describe(), use_container_width=True)


if st.secrets.get("validate"):
    st.subheader("Validation")
    with st.spinner(f"validating {filename}..."):
        st.dataframe(feed.validate(), use_container_width=True)

with st.spinner(f"Computing trip stats..."):
    trip_stats = get_trip_stats(feed)

st.subheader("Stops")
st.text(f"There are {feed.get_stops()['stop_id'].nunique()} stops.")
m = feed.map_stops(feed.get_stops()["stop_id"])
st_folium(m)

st.subheader("Routes")
geometrize_routes = feed.geometrize_routes()
duplicated = geometrize_routes["route_short_name"].duplicated()
geometrize_routes = geometrize_routes[~duplicated]
st.text(f"There are {geometrize_routes['route_short_name'].nunique()} routes.")

fig = px.histogram(
    trip_stats.groupby(["route_short_name", "speed"]).nunique().reset_index(),
    x="speed",
    labels={
        "speed": "Speed (km/h)",
    },
)
fig

fig = px.histogram(
    trip_stats.groupby(["route_short_name", "distance"])
    .nunique()
    .reset_index()
    .groupby("route_short_name")
    .count()
    .reset_index(),
    x="distance",
    color="distance",
    labels={
        "distance": "Number of Trips",
    },
)
fig
st.text("Each route could have different numbers of trips.")

selected_routes = st.multiselect(
    "Choose routes for info about their longest trips",
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
    def get_route_short_name(name):
        return name.split()[0]

    route_short_names = [get_route_short_name(name) for name in selected_routes]
    routes = geometrize_routes[
        geometrize_routes["route_short_name"].isin(route_short_names)
    ]
    m = folium.Map((lat, lon))

    def get_locations(coords):
        return [(b, a) for a, b in coords]

    color_ind = 0
    colors_used = {}
    for row in routes[["route_short_name", "geometry"]].to_dict("records"):
        geometry = row["geometry"]
        name = row["route_short_name"]
        coords = mapping(geometry)["coordinates"]
        color = colors[color_ind % color_size]
        colors_used[name] = color
        try:
            folium.PolyLine(get_locations(coords), color=color).add_to(m)
        except ValueError:
            for _coords in coords:
                folium.PolyLine(get_locations(_coords), color=color).add_to(m)
        finally:
            color_ind += 1
    st_folium(m)

    selected_trip_stats = (
        trip_stats[trip_stats["route_short_name"].isin(route_short_names)]
        .groupby(["route_short_name"])
        .max()
    )

    for name, route_short_name in zip(selected_routes, route_short_names):
        _stats = selected_trip_stats.loc[route_short_name]
        distance = _stats["distance"]
        duration = _stats["duration"] * 60
        speed = _stats["speed"]
        loop = "Yes" if _stats["is_loop"] else "No"
        color = colors_used[route_short_name]
        st.caption(
            f'<p style="color:{color};">{name}</p>',
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Distance (km)", f"{distance:.2f}")
        col2.metric("Duration (mins)", f"{duration:.2f}")
        col3.metric("Speed (km/h)", f"{speed:.2f}")
        col4.metric("Loop?", loop)
