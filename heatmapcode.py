"""
Real-Time Atmospheric Pollutant Heatmap — plotted on the map of India
-----------------------------------------------------------------------
Two outputs:
  1. india_aqi_geo_heatmap.png   — static map (geopandas + matplotlib, actual
                                    Indian state boundaries)
  2. india_aqi_geo_heatmap.html  — interactive, zoomable map (Plotly)

DATA MODES
----------
SAMPLE MODE (default): uses india_air_quality_sample.csv bundled alongside this
script, so it runs immediately with no download needed.

REAL KAGGLE MODE: download "city_day.csv" from
  https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india
and set CSV_PATH below to that file. Columns City/Date/PM2.5/PM10/AQI/AQI_Bucket
are auto-detected and merged with the CITY_COORDS lookup.

India state-boundary polygons are pulled once from a public GitHub GeoJSON
mirror (no Kaggle/Google auth needed) and cached locally as india_states.geojson.
"""

import json
import urllib.request
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# 1. CONFIG
# ---------------------------------------------------------------------------
CSV_PATH = "india_air_quality_sample.csv"   # <-- point this at "city_day.csv" for real Kaggle data
USE_LATEST_DATE_ONLY = True
GEOJSON_PATH = "india_states.geojson"
GEOJSON_URL = ("https://raw.githubusercontent.com/Subhash9325/"
               "GeoJson-Data-of-Indian-States/master/Indian_States")

CITY_COORDS = {
    "Ahmedabad": (23.0225, 72.5714), "Aizawl": (23.7271, 92.7176), "Amaravati": (16.5062, 80.6480),
    "Amritsar": (31.6340, 74.8723), "Bangalore": (12.9716, 77.5946), "Bengaluru": (12.9716, 77.5946),
    "Bhopal": (23.2599, 77.4126), "Brajrajnagar": (21.8167, 83.9167), "Chandigarh": (30.7333, 76.7794),
    "Chennai": (13.0827, 80.2707), "Coimbatore": (11.0168, 76.9558), "Delhi": (28.6139, 77.2090),
    "New Delhi": (28.6139, 77.2090), "Ernakulam": (9.9816, 76.2999), "Gurugram": (28.4595, 77.0266),
    "Guwahati": (26.1445, 91.7362), "Hyderabad": (17.3850, 78.4867), "Indore": (22.7196, 75.8577),
    "Jaipur": (26.9124, 75.7873), "Jorapokhar": (23.7000, 86.4167), "Kanpur": (26.4499, 80.3319),
    "Kochi": (9.9312, 76.2673), "Kolkata": (22.5726, 88.3639), "Lucknow": (26.8467, 80.9462),
    "Mumbai": (19.0760, 72.8777), "Nagpur": (21.1458, 79.0882), "Patna": (25.5941, 85.1376),
    "Pune": (18.5204, 73.8567), "Shillong": (25.5788, 91.8933), "Talcher": (20.9500, 85.2167),
    "Thiruvananthapuram": (8.5241, 76.9366), "Visakhapatnam": (17.6868, 83.2185),
}

# ---------------------------------------------------------------------------
# 2. LOAD POLLUTANT DATA
# ---------------------------------------------------------------------------
df = pd.read_csv(CSV_PATH)

if "Date" in df.columns and USE_LATEST_DATE_ONLY:
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").groupby("City", as_index=False).last()

if "Latitude" not in df.columns or "Longitude" not in df.columns:
    df["Latitude"] = df["City"].map(lambda c: CITY_COORDS.get(c, (None, None))[0])
    df["Longitude"] = df["City"].map(lambda c: CITY_COORDS.get(c, (None, None))[1])
df = df.dropna(subset=["Latitude", "Longitude", "AQI"])

def cpcb_bucket(aqi):
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Satisfactory"
    elif aqi <= 200: return "Moderate"
    elif aqi <= 300: return "Poor"
    elif aqi <= 400: return "Very Poor"
    else: return "Severe"

if "AQI_Bucket" not in df.columns:
    df["AQI_Bucket"] = df["AQI"].apply(cpcb_bucket)

gdf_points = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]), crs="EPSG:4326"
)

# ---------------------------------------------------------------------------
# 3. GET INDIA STATE BOUNDARIES (downloaded once, then cached)
# ---------------------------------------------------------------------------
try:
    india_states = gpd.read_file(GEOJSON_PATH)
except Exception:
    urllib.request.urlretrieve(GEOJSON_URL, GEOJSON_PATH)
    india_states = gpd.read_file(GEOJSON_PATH)

# ---------------------------------------------------------------------------
# 4. STATIC MAP — geopandas + matplotlib
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 9))
india_states.boundary.plot(ax=ax, linewidth=0.5, color="grey")
india_states.plot(ax=ax, color="whitesmoke", edgecolor="grey", linewidth=0.5, zorder=0)

sizes = (gdf_points["AQI"] / gdf_points["AQI"].max()) * 500 + 60
sc = ax.scatter(
    gdf_points["Longitude"], gdf_points["Latitude"],
    c=gdf_points["AQI"], cmap="YlOrRd", s=sizes,
    edgecolor="black", linewidth=0.6, alpha=0.85, zorder=3,
    vmin=0, vmax=max(200, gdf_points["AQI"].max()),
)
for _, row in gdf_points.iterrows():
    ax.annotate(row["City"], (row["Longitude"], row["Latitude"]),
                fontsize=7, ha="left", va="bottom",
                xytext=(3, 3), textcoords="offset points")

cbar = plt.colorbar(sc, ax=ax, shrink=0.6, pad=0.02)
cbar.set_label("AQI (higher = more harmful)")
ax.set_title("Real-Time Atmospheric Pollutant Heatmap\nIndian Cities — AQI Severity", fontsize=13, fontweight="bold")
ax.set_xlim(68, 98)
ax.set_ylim(6, 38)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
plt.tight_layout()
plt.savefig("india_aqi_geo_heatmap.png", dpi=200)
print("Saved static map: india_aqi_geo_heatmap.png")

# ---------------------------------------------------------------------------
# 5. INTERACTIVE MAP — Plotly (zoomable, hoverable; open the .html in a browser)
# ---------------------------------------------------------------------------
fig2 = go.Figure(go.Scattergeo(
    lon=df["Longitude"], lat=df["Latitude"],
    text=df.apply(lambda r: f"{r['City']}<br>AQI: {r['AQI']} ({r['AQI_Bucket']})"
                             f"<br>PM2.5: {r.get('PM2.5','-')} µg/m³", axis=1),
    mode="markers",
    marker=dict(size=sizes / 12, color=df["AQI"], colorscale="YlOrRd",
                cmin=0, cmax=max(200, df["AQI"].max()),
                colorbar=dict(title="AQI"), line=dict(width=0.8, color="black"), opacity=0.85),
    hoverinfo="text",
))
fig2.update_geos(scope="asia", lonaxis_range=[68, 98], lataxis_range=[6, 38],
                  showcountries=True, countrycolor="black", showland=True,
                  landcolor="rgb(245,245,240)", showsubunits=True, subunitcolor="lightgrey")
fig2.update_layout(title="Real-Time Atmospheric Pollutant Heatmap — Indian Cities (interactive)",
                    title_x=0.5, height=700, width=650, margin=dict(l=0, r=0, t=60, b=0))
fig2.write_html("india_aqi_geo_heatmap.html")
print("Saved interactive map: india_aqi_geo_heatmap.html")

print("\n", df[["City", "AQI", "AQI_Bucket"]].sort_values("AQI", ascending=False).to_string(index=False))

# ===========================================================================
# 6. FUTURE AIR-QUALITY FORECAST  (NEW -- everything above is unchanged)
# ---------------------------------------------------------------------------
# Forecast = f( human emissions, weather, topography, natural events )
#
#   Human emissions : per-city emission load (traffic + power plants + industry)
#   Weather         : wind / rain clear pollution; heat + stagnant air trap it
#                     (live Open-Meteo forecast, falls back to monthly climatology)
#   Topography      : basin / valley trapping factor amplifies stagnation
#   Natural events  : seasonal crop-burn smoke, dust storms, wildfire smoke, plus
#                     EVENT_OVERRIDE for sudden events (dust storm, ash cloud...)
#
# Two engines, picked automatically:
#   * ML  (HistGradientBoosting) if the CSV has enough daily history
#           -> real Kaggle city_day.csv
#   * Rule-based factor model otherwise
#           -> small sample CSV
# ===========================================================================
import numpy as np
from datetime import date, timedelta
from functools import lru_cache
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

FORECAST_DAYS = 7
USE_LIVE_WEATHER = True      # Open-Meteo (free, no API key); offline -> climatology
EVENT_OVERRIDE = {}          # sudden-event injection, e.g. {"Delhi": 0.35} = +35% AQI
TODAY = date.today()

ALIASES = {"New Delhi": "Delhi", "Bangalore": "Bengaluru"}

# (emission_load, topographic_trapping), both 0-1.  Expert estimates -- tune freely.
SITE = {
    "Delhi": (1.00, 0.80), "Gurugram": (0.85, 0.80), "Kanpur": (0.85, 0.85),
    "Lucknow": (0.75, 0.85), "Patna": (0.80, 0.80), "Kolkata": (0.80, 0.55),
    "Mumbai": (0.60, 0.15), "Ahmedabad": (0.75, 0.35), "Jaipur": (0.60, 0.40),
    "Amritsar": (0.60, 0.70), "Chandigarh": (0.50, 0.50), "Bengaluru": (0.55, 0.20),
    "Hyderabad": (0.60, 0.35), "Chennai": (0.55, 0.15), "Pune": (0.55, 0.50),
    "Nagpur": (0.55, 0.35), "Bhopal": (0.45, 0.40), "Indore": (0.55, 0.30),
    "Guwahati": (0.50, 0.70), "Shillong": (0.20, 0.30), "Aizawl": (0.15, 0.20),
    "Amaravati": (0.35, 0.20), "Visakhapatnam": (0.55, 0.20), "Coimbatore": (0.40, 0.20),
    "Kochi": (0.35, 0.10), "Ernakulam": (0.35, 0.10), "Thiruvananthapuram": (0.25, 0.10),
    "Talcher": (0.90, 0.50), "Jorapokhar": (0.85, 0.50), "Brajrajnagar": (0.80, 0.45),
}
def site(city):
    return SITE.get(ALIASES.get(city, city), (0.40, 0.40))

# Natural events: city exposure (0-1) x seasonal weight (by month) x max AQI uplift
EVENT_EXPOSURE = {
    "stubble":  {"Amritsar": 1.0, "Delhi": 0.9, "Chandigarh": 0.8, "Gurugram": 0.8,
                 "Lucknow": 0.5, "Kanpur": 0.5, "Patna": 0.3},
    "dust":     {"Jaipur": 1.0, "Delhi": 0.8, "Gurugram": 0.8, "Ahmedabad": 0.7,
                 "Amritsar": 0.5, "Lucknow": 0.5, "Kanpur": 0.5, "Indore": 0.4,
                 "Bhopal": 0.4, "Nagpur": 0.3},
    "wildfire": {"Aizawl": 0.6, "Shillong": 0.6, "Guwahati": 0.5, "Talcher": 0.5,
                 "Brajrajnagar": 0.5, "Chandigarh": 0.4, "Bhopal": 0.3},
}
EVENT_SEASON = {"stubble": {10: 0.5, 11: 1.0}, "dust": {4: 0.6, 5: 1.0, 6: 0.8},
                "wildfire": {2: 0.5, 3: 1.0, 4: 0.8}}
EVENT_MAX_UPLIFT = {"stubble": 0.45, "dust": 0.35, "wildfire": 0.25}

def fmonth(d):
    """Fractional month: equals the month number at mid-month, so seasons change smoothly."""
    dim = pd.Period(d, "D").days_in_month
    return d.month + (d.day - 0.5) / dim - 0.5

def _interp(vals12, fm):
    x = (fm - 1) % 12
    i = int(np.floor(x)); f = x - i
    return vals12[i] * (1 - f) + vals12[(i + 1) % 12] * f

def event_uplift(city, fm):
    c = ALIASES.get(city, city)
    up = sum(EVENT_MAX_UPLIFT[e] * EVENT_EXPOSURE[e].get(c, 0) *
             _interp([EVENT_SEASON[e].get(m, 0) for m in range(1, 13)], fm)
             for e in EVENT_EXPOSURE)
    return min(up, 0.8)

# Monthly climatology fallback: (max wind km/h, rain mm/day, max temp C), Jan..Dec
CLIMO = {
    "north": [(14,.8,20),(16,.8,24),(18,.6,31),(20,.4,37),(22,1,40),(22,4,38),
              (18,11,34),(16,11,33),(15,6,33),(13,1,32),(12,.2,27),(12,.4,22)],
    "south": [(20,1,31),(20,.5,33),(20,1,35),(20,3,36),(22,5,36),(26,8,33),
              (26,8,32),(24,8,32),(20,8,32),(16,10,31),(16,8,30),(18,3,30)],
}
def climo(lat, fm):
    tab = CLIMO["north" if lat >= 20 else "south"]
    w, r, t = (_interp([row[k] for row in tab], fm) for k in range(3))
    return dict(wind=w, rain=r, tmax=t)

def weather_effect(wx, topo, fm):
    """AQI multiplier from weather. >1 traps pollution, <1 clears it."""
    vent = min(wx["wind"] / 25.0, 1.0)                    # wind ventilation
    rain = min(wx["rain"] / 10.0, 1.0)                    # rain wash-out
    clear = 0.6 * vent + 0.4 * rain
    heat = min(max((wx["tmax"] - 32) / 8.0, 0.0), 1.0)    # heat / smog formation
    winter = _interp([1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1], fm)       # Nov-Feb
    inversion = topo * (1 - vent) * winter                             # winter lid
    mult = 1 + (0.5 * (0.4 - clear) + 0.25 * heat + 0.25 * inversion) * (0.5 + topo)
    return float(np.clip(mult, 0.5, 1.8)), clear, heat, inversion

_wx_ok = [USE_LIVE_WEATHER]
def get_weather(lat, lon, days):
    clim = [climo(lat, fmonth(d)) for d in days]
    if _wx_ok[0]:
        try:
            url = ("https://api.open-meteo.com/v1/forecast?latitude={:.3f}&longitude={:.3f}"
                   "&daily=temperature_2m_max,precipitation_sum,wind_speed_10m_max"
                   "&forecast_days={}&timezone=auto").format(lat, lon, len(days) + 1)
            with urllib.request.urlopen(url, timeout=8) as resp:
                dly = json.load(resp)["daily"]
            out = []
            for h, c in enumerate(clim, start=1):          # index 0 = today
                live = dict(wind=dly["wind_speed_10m_max"][h],
                            rain=dly["precipitation_sum"][h], tmax=dly["temperature_2m_max"][h])
                out.append({k: (live[k] if live[k] is not None else c[k]) for k in c})
            return out
        except Exception:
            _wx_ok[0] = False
            print("Live weather unavailable -> using monthly climatology")
    return clim

def main_driver(em, topo, wm, ev):
    if ev >= 0.15: return "Natural event (smoke/dust)"
    if wm >= 1.15: return "Stagnant / hot weather"
    if wm <= 0.85: return "Wind / rain clearing"
    if topo >= 0.70: return "Valley / basin trapping"
    if em >= 0.70: return "Heavy emissions"
    return "Typical conditions"

# ---- history (for ML mode / city baselines) -------------------------------
hist = pd.read_csv(CSV_PATH)
ML_READY = False
if {"Date", "City", "AQI"} <= set(hist.columns):
    hist["Date"] = pd.to_datetime(hist["Date"], errors="coerce")
    hist = hist.dropna(subset=["Date", "AQI"]).sort_values(["City", "Date"])
    ML_READY = hist["Date"].nunique() >= 120 and len(hist) >= 1000

@lru_cache(maxsize=None)
def static_row(city, month, lat):   # month may be fractional
    em, topo = site(city)
    _, clear, heat, inv = weather_effect(climo(lat, month), topo, month)
    return (em, topo, clear, heat, inv, event_uplift(city, month),
            float(np.sin(2 * np.pi * month / 12)), float(np.cos(2 * np.pi * month / 12)))

def build_training(h_df):
    X, y, dts = [], [], []
    for city, g in h_df.groupby("City"):
        lat = float(g["Latitude"].iloc[0]) if "Latitude" in g else CITY_COORDS.get(city, (22.0, 0))[0]
        s = g.groupby("Date")["AQI"].mean().asfreq("D").interpolate(limit=3)
        m7 = s.rolling(7, min_periods=3).mean()
        for h in range(1, FORECAST_DAYS + 1):
            tgt = s.shift(-h)
            ok = (s.notna() & tgt.notna() & m7.notna()).values
            if ok.sum() == 0:
                continue
            idx = s.index[ok]
            months = (idx + pd.Timedelta(days=h)).month
            stat = np.array([static_row(city, int(m), lat) for m in months])
            X.append(np.column_stack([s.values[ok], m7.values[ok], np.full(ok.sum(), h), stat]))
            y.append(tgt.values[ok]); dts.append(idx.values)
    return np.vstack(X), np.concatenate(y), np.concatenate(dts)

model = None
if ML_READY:
    X, y, dts = build_training(hist)
    order = np.argsort(dts); cut = int(0.8 * len(order))
    tr, te = order[:cut], order[cut:]
    m_eval = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, random_state=0)
    m_eval.fit(X[tr], y[tr])
    print(f"\nForecast engine: ML (HistGradientBoosting)  |  hold-out MAE = "
          f"{mean_absolute_error(y[te], m_eval.predict(X[te])):.1f} AQI  "
          f"(persistence baseline = {mean_absolute_error(y[te], X[te][:, 0]):.1f})")
    model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, random_state=0).fit(X, y)
else:
    print("\nForecast engine: rule-based factor model (not enough daily history for ML)")

# ---- forecast every city ---------------------------------------------------
days = [TODAY + timedelta(days=h) for h in range(1, FORECAST_DAYS + 1)]
records = []
for _, r in df.iterrows():
    city, lat, lon, now = r["City"], float(r["Latitude"]), float(r["Longitude"]), float(r["AQI"])
    em, topo = site(city)
    ch = hist[hist["City"] == city]["AQI"].dropna()
    m7 = float(ch.tail(7).mean()) if len(ch) else now
    struct = float(ch.mean()) if len(ch) >= 10 else 50 + 250 * em * (0.6 + 0.4 * topo)
    wx_list = get_weather(lat, lon, days)
    boost = EVENT_OVERRIDE.get(city, 0.0)
    for h, (d, wx) in enumerate(zip(days, wx_list), start=1):
        wm_live = weather_effect(wx, topo, fmonth(d))[0]
        ev = event_uplift(city, fmonth(d)) + boost
        if model is not None:
            base = float(model.predict([[now, m7, h, *static_row(city, fmonth(d), lat)]])[0])
            wm_clim = weather_effect(climo(lat, fmonth(d)), topo, fmonth(d))[0]
            pred = base * float(np.clip(wm_live / wm_clim, 0.7, 1.4)) * (1 + boost)
        else:
            target = struct * wm_live * (1 + min(ev, 1.0))
            w = np.exp(-h / 3.0)                       # persistence fades with horizon
            pred = w * now + (1 - w) * target
        pred = float(np.clip(pred, 10, 500))
        records.append(dict(City=city, Latitude=lat, Longitude=lon, Date=d, Day=h,
                            AQI_Forecast=int(round(pred)), Bucket=cpcb_bucket(pred),
                            Driver=main_driver(em, topo, wm_live, ev),
                            Wind_kmh=wx["wind"], Rain_mm=wx["rain"], Tmax_C=wx["tmax"]))

forecast = pd.DataFrame(records)
forecast.to_csv("india_aqi_forecast.csv", index=False)
print("Saved forecast table: india_aqi_forecast.csv")

summary = forecast.pivot(index="City", columns="Day", values="AQI_Forecast")
summary = summary[[c for c in (1, 3, FORECAST_DAYS) if c in summary.columns]]
summary.columns = [f"D+{c}" for c in summary.columns]
summary.insert(0, "Now", df.set_index("City")["AQI"].round().astype(int))
summary["Main driver (D+1)"] = forecast[forecast.Day == 1].set_index("City")["Driver"]
print(f"\nAQI forecast from {TODAY:%d %b %Y}:\n",
      summary.sort_values(summary.columns[-2], ascending=False).to_string())

# ---- static forecast map: tomorrow vs. last forecast day -------------------
fig3, axes = plt.subplots(1, 2, figsize=(14, 8))
vmax = max(200, forecast["AQI_Forecast"].max())
for axk, day in zip(axes, [1, FORECAST_DAYS]):
    f = forecast[forecast.Day == day]
    india_states.plot(ax=axk, color="whitesmoke", edgecolor="grey", linewidth=0.5, zorder=0)
    sc3 = axk.scatter(f["Longitude"], f["Latitude"], c=f["AQI_Forecast"], cmap="YlOrRd",
                      s=(f["AQI_Forecast"] / vmax) * 500 + 60, edgecolor="black",
                      linewidth=0.6, alpha=0.85, zorder=3, vmin=0, vmax=vmax)
    for _, row in f.iterrows():
        axk.annotate(row["City"], (row["Longitude"], row["Latitude"]), fontsize=7,
                     ha="left", va="bottom", xytext=(3, 3), textcoords="offset points")
    axk.set_xlim(68, 98); axk.set_ylim(6, 38)
    axk.set_title(f"Forecast AQI - {f['Date'].iloc[0]:%d %b %Y} (D+{day})", fontweight="bold")
    axk.set_xlabel("Longitude"); axk.set_ylabel("Latitude")
fig3.colorbar(sc3, ax=axes, shrink=0.6, pad=0.02, label="Forecast AQI (higher = more harmful)")
fig3.suptitle("Predicted Air Quality - Emissions + Weather + Topography + Natural Events",
              fontsize=13, fontweight="bold")
plt.savefig("india_aqi_forecast_map.png", dpi=200)
print("Saved forecast map: india_aqi_forecast_map.png")

# ---- interactive forecast map with day slider (Plotly) --------------------
def _frame(day):
    f = forecast[forecast.Day == day]
    return go.Frame(name=f"{f['Date'].iloc[0]:%d %b}", data=[go.Scattergeo(
        lon=f["Longitude"], lat=f["Latitude"], mode="markers", hoverinfo="text",
        text=f.apply(lambda q: f"{q['City']}<br>Forecast AQI: {q['AQI_Forecast']} ({q['Bucket']})"
                               f"<br>Driver: {q['Driver']}<br>Wind {q['Wind_kmh']} km/h | "
                               f"Rain {q['Rain_mm']} mm | Tmax {q['Tmax_C']} C", axis=1),
        marker=dict(size=8 + f["AQI_Forecast"] / 12, color=f["AQI_Forecast"], colorscale="YlOrRd",
                    cmin=0, cmax=vmax, colorbar=dict(title="AQI"),
                    line=dict(width=0.8, color="black"), opacity=0.85))])
frames = [_frame(d) for d in range(1, FORECAST_DAYS + 1)]
fig4 = go.Figure(data=frames[0].data, frames=frames)
fig4.update_geos(scope="asia", lonaxis_range=[68, 98], lataxis_range=[6, 38],
                 showcountries=True, countrycolor="black", showland=True,
                 landcolor="rgb(245,245,240)", showsubunits=True, subunitcolor="lightgrey")
fig4.update_layout(
    title="Predicted Air Quality - Indian Cities (drag the slider)", title_x=0.5,
    height=720, width=650, margin=dict(l=0, r=0, t=60, b=0),
    sliders=[dict(active=0, currentvalue=dict(prefix="Date: "), steps=[
        dict(method="animate", label=fr.name,
             args=[[fr.name], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
        for fr in frames])],
    updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=0.02, buttons=[dict(
        label="Play", method="animate",
        args=[None, dict(frame=dict(duration=900, redraw=True), fromcurrent=True)])])])
fig4.write_html("india_aqi_forecast.html")
print("Saved interactive forecast: india_aqi_forecast.html")