"""
RICE CARBON CREDIT CALCULATOR  (Streamlit version)
Methodologies: Simplified Gold Standard | General Gold Standard | Isometric

Run with:
    pip install streamlit pandas
    streamlit run rice_carbon_calculator.py
"""

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Rice Carbon Credit Calculator", page_icon="🌾", layout="wide")

# ============================================================
# DATA TABLES
# ============================================================
COUNTRY_EF = {
    "Bangladesh": 0.97, "Brazil": 1.62, "China": 1.30, "India": 0.85,
    "Indonesia": 1.18, "Italy": 1.66, "Japan": 1.06, "Philippines": 0.60,
    "South Korea": 1.83, "Spain": 1.13, "Uruguay": 0.80, "USA": 0.65,
    "Vietnam": 1.13,
}

RICE_SEASONS = {
    "Single season rice in a year": 1,
    "Double season rice in a year": 2,
    "Triple season rice in a year": 3,
}

WATER_REGIME_ONSEASON = {
    "Continuously flooded": 1.00,
    "Single drainage period": 0.71,
    "Multiple drainage periods": 0.55,
}

PRESEASON_GENERAL = {
    "Non flooded pre-season of rice < 180 days before cultivation": 1.00,
    "Non flooded pre-season of rice > 180 days before cultivation": 0.89,
}

PRESEASON_ISOMETRIC = {
    "Non flooded pre-season of rice < 180 days before cultivation": 1.00,
    "Non flooded pre-season of rice > 180 days before cultivation": 0.89,
    "Non flooded pre-season of rice > 365 days before cultivation": 0.59,
    "Non flooded pre-season of rice > 30 days before cultivation": 2.41,
}

GWP_CH4 = 27
GWP_N2O = 273
DIESEL_EF = 0.0026606   # tCO2/L
PETROL_EF = 0.002210    # tCO2/L
UNCERTAINTY = 0.15

METHODOLOGIES = ["Simplified Gold Standard", "General Gold Standard", "Isometric"]


# ============================================================
# INPUT HELPERS
# ============================================================
def organic_amendment_inputs(prefix: str) -> float:
    """Renders organic amendment inputs and returns the organic amendment factor."""
    c1, c2 = st.columns(2)
    with c1:
        straw_lt30 = st.number_input(
            "Straw incorporated <30 days before cultivation (dry t/ha/season)",
            min_value=0.5, value=0.5, step=0.1, key=f"{prefix}_straw_lt30")
        compost = st.number_input(
            "Compost (fresh t/ha/season)",
            min_value=0.0, value=0.0, step=0.1, key=f"{prefix}_compost")
        green_manure = st.number_input(
            "Green manure (fresh t/ha/season)",
            min_value=0.0, value=0.0, step=0.1, key=f"{prefix}_gm")
    with c2:
        straw_gt30 = st.number_input(
            "Straw incorporated >30 days before cultivation (dry t/ha/season)",
            min_value=0.5, value=0.5, step=0.1, key=f"{prefix}_straw_gt30")
        fym = st.number_input(
            "FYM (fresh t/ha/season)",
            min_value=0.0, value=0.0, step=0.1, key=f"{prefix}_fym")

    factor = (
        1
        + straw_lt30 * 1
        + straw_gt30 * 0.19
        + compost * 0.17
        + fym * 0.21
        + green_manure * 0.45
    ) ** 0.59
    st.caption(f"Organic amendment factor: **{factor:.6f}**")
    return factor


def scenario_inputs(prefix: str, preseason_options: dict, ask_n: bool):
    """Renders water regime, pre-season, organic amendment (and N) inputs."""
    onseason_label = st.selectbox(
        "Water regime during rice cultivation",
        list(WATER_REGIME_ONSEASON.keys()), key=f"{prefix}_onseason")
    onseason = WATER_REGIME_ONSEASON[onseason_label]

    preseason_label = st.selectbox(
        "Pre-season water regime",
        list(preseason_options.keys()), key=f"{prefix}_preseason")
    preseason = preseason_options[preseason_label]

    st.markdown("**Organic amendment / straw**")
    organic = organic_amendment_inputs(prefix)

    n_applied = 0.0
    if ask_n:
        n_applied = st.number_input(
            "Total N applied (kg N/ha/season)",
            min_value=0.0, value=0.0, step=1.0, key=f"{prefix}_n")

    return onseason, preseason, organic, n_applied


def ch4_emission(country_factor, seasons, duration, onseason, preseason, organic):
    return (country_factor * seasons * duration * onseason * preseason
            * organic * GWP_CH4 * 1e-3)


# ============================================================
# SIDEBAR - COMMON INPUTS
# ============================================================
st.title("🌾 Carbon Credit Calculator : AWD in Rice")

with st.sidebar:
    st.header("Common inputs")
    methodology = st.selectbox("Methodology", METHODOLOGIES)
    country = st.selectbox("Country", list(COUNTRY_EF.keys()))
    country_factor = COUNTRY_EF[country]
    st.caption(f"Country-specific emission factor: **{country_factor}**")

    seasons_label = st.selectbox("Rice cultivation frequency", list(RICE_SEASONS.keys()))
    rice_seasons = RICE_SEASONS[seasons_label]

    duration = st.number_input(
        "Average rice duration per season (days)", min_value=1, value=120, step=1)

is_simplified = methodology == "Simplified Gold Standard"
is_general = methodology == "General Gold Standard"
is_isometric = methodology == "Isometric"
ask_n = not is_simplified
preseason_options = PRESEASON_ISOMETRIC if is_isometric else PRESEASON_GENERAL

st.info(f"Selected methodology: **{methodology}**")

# ============================================================
# BASELINE & PROJECT INPUTS
# ============================================================
col_base, col_proj = st.columns(2, gap="large")

with col_base:
    st.subheader("Baseline scenario")
    (base_onseason, base_preseason,
     base_organic, base_n) = scenario_inputs("base", preseason_options, ask_n)

with col_proj:
    st.subheader("Project scenario")
    (proj_onseason, proj_preseason,
     proj_organic, proj_n) = scenario_inputs("proj", preseason_options, ask_n)

    diesel = petrol = 0.0
    if not is_simplified:
        st.markdown("**Fuel consumption**")
        f1, f2 = st.columns(2)
        with f1:
            diesel = st.number_input("Diesel (L/ha/season)", min_value=0.0,
                                     value=0.0, step=1.0, key="diesel")
        with f2:
            petrol = st.number_input("Petrol (L/ha/season)", min_value=0.0,
                                     value=0.0, step=1.0, key="petrol")

st.divider()

# ============================================================
# CALCULATION
# ============================================================
if st.button("Calculate carbon credit", type="primary", use_container_width=True):

    # ---- Baseline CH4 ----
    total_emission_base = ch4_emission(
        country_factor, rice_seasons, duration,
        base_onseason, base_preseason, base_organic)

    # ---- Project CH4 ----
    proj_ch4 = ch4_emission(
        country_factor, rice_seasons, duration,
        proj_onseason, proj_preseason, proj_organic)

    proj_n2o = 0.0
    proj_co2 = 0.0

    if is_general:
        if proj_n >= base_n:
            proj_n2o = (proj_n - base_n) * 0.00786 * GWP_N2O * 1e-3
        else:
            proj_n2o = proj_n * 0.00314 * GWP_N2O * 1e-3
        proj_co2 = diesel * DIESEL_EF + petrol * PETROL_EF

    elif is_isometric:
        conv = 44 / 28
        if proj_n >= base_n:
            proj_n2o = ((proj_n - base_n) * 0.00786 * conv * GWP_N2O * 1e-3
                        + proj_n * 0.00314 * conv * GWP_N2O * 1e-3)
        else:
            proj_n2o = proj_n * 0.00314 * conv * GWP_N2O * 1e-3
        proj_co2 = diesel * DIESEL_EF + petrol * PETROL_EF

    total_emission_proj = proj_ch4 + proj_n2o + proj_co2

    # ---- Credits ----
    gross_credit = total_emission_base - total_emission_proj
    net_credit = gross_credit * (1 - UNCERTAINTY)

    # ---- Results ----
    st.header("Final result")

    m1, m2, m3 = st.columns(3)
    m1.metric("Baseline emission", f"{total_emission_base:.4f}", help="tCO2e/ha/year")
    m2.metric("Project emission", f"{total_emission_proj:.4f}", help="tCO2e/ha/year")
    m3.metric("Gross carbon credit", f"{gross_credit:.4f}", help="tCO2e/ha/year")

    if net_credit >= 0:
        st.success(f"**Net carbon credit (after 15% uncertainty deduction): "
                   f"{net_credit:.4f} tCO2e/ha/year**")
    else:
        st.error(f"**Net carbon credit: {net_credit:.4f} tCO2e/ha/year** "
                 "(project emits more than baseline - no credit generated)")

    st.subheader("Project emission breakdown (tCO2e/ha/year)")
    breakdown = pd.DataFrame({
        "Source": ["CH4", "N2O", "Fuel CO2", "Total project"],
        "Emission": [proj_ch4, proj_n2o, proj_co2, total_emission_proj],
    })
    st.dataframe(breakdown.style.format({"Emission": "{:.4f}"}),
                 hide_index=True, use_container_width=True)

    st.subheader("Summary")
    summary = pd.DataFrame({
        "Parameter": [
            "Methodology", "Country", "Country emission factor",
            "Rice seasons per year", "Rice duration per season",
            "Baseline emission", "Project emission",
            "Gross carbon credit", "Uncertainty deduction", "Net carbon credit",
        ],
        "Value": [
            methodology, country, str(country_factor),
            str(rice_seasons), f"{duration} days",
            f"{total_emission_base:.4f} tCO2e/ha/year",
            f"{total_emission_proj:.4f} tCO2e/ha/year",
            f"{gross_credit:.4f} tCO2e/ha/year",
            f"{UNCERTAINTY:.0%}",
            f"{net_credit:.4f} tCO2e/ha/year",
        ],
    })
    st.dataframe(summary, hide_index=True, use_container_width=True)

    st.download_button(
        "Download summary (CSV)",
        summary.to_csv(index=False).encode("utf-8"),
        file_name="rice_carbon_credit_summary.csv",
        mime="text/csv",
    )