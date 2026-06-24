import streamlit as st
import pandas as pd
import os
import altair as alt


@st.cache_data
def get_data(path, time):

    df = pd.read_csv("data_500_days.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    
    # assume the following:
    # Cradle to gate emissions for PLA filaments = 3.9 kg Co2eq / kg https://www.researchgate.net/publication/393510051_Sustainability_Assessment_of_the_3D-_Recycler_Process_Local_Plastic_Recycling_for_3D_Printing
    # Cradle to gate emissions for TPU filaments = 4.65 kg Co2eq/kg source: https://www.carbonfact.com/blog/knowledge/tpu-midsoles
    # Cradle to gate emissions for PetG filaments = 6.27 kg Co2eq/kg source: https://www.filamentive.com/reduce-co2-emissions-by-3d-printing-with-recycled-materials/


    # recycled PLA filament emissions: 1.1kg co2eq/kg https://www.researchgate.net/publication/393510051_Sustainability_Assessment_of_the_3D-_Recycler_Process_Local_Plastic_Recycling_for_3D_Printing
    # recycled TPU filament emissions: 3.4 (reducing about 26% for 50% Recycled TPU ) https://www.carbonfact.com/blog/knowledge/tpu-midsoles
    # Recycled PetG filament emissions: 4.08kg co2eq /kg https://www.filamentive.com/reduce-co2-emissions-by-3d-printing-with-recycled-materials/
    v_PLA = 3.9
    v_TPU = 4.65
    v_PETG = 6.27
    r_PLA = 1.1
    r_PETG = 4.08
    r_TPU = 3.4

    v_PVA = 2.47
    total_pla = df["PLA_weight"].sum()
    total_tpu = df["TPU_weight"].sum()
    total_petg = df["PETG_weight"].sum()
    total_pure_weight = total_pla + total_tpu + total_petg


    v_Mixed = (0.01 * v_PVA) + 0.99 * (
            (total_pla * v_PLA + total_tpu * v_TPU + total_petg * v_PETG)
            / total_pure_weight
        ) # weighted sum to estimate the kgCo2eq contribution of mixed waste.
    r_Mixed = v_Mixed

    ed_d = {
        "Date": df["Date"],
        "PLA_emissions": df["PLA_weight"] * v_PLA * 1e-3,
        "PETG_emissions": df["PETG_weight"] * v_PETG * 1e-3,
        "TPU_emissions": df["TPU_weight"] * v_TPU * 1e-3,
        "Mixed_emissions": df["Mixed_weight"] * v_Mixed * 1e-3,
    }  # emissions data, daily
    ed_ds = {
        "Date": df["Date"],
        "PLA_savings": df["PLA_weight"] * (v_PLA - r_PLA) * 1e-3,
        "PETG_savings": df["PETG_weight"] * (v_PETG - r_PETG) * 1e-3,
        "TPU_savings": df["TPU_weight"] * (v_TPU - r_TPU) * 1e-3,
        "Mixed_savings": df["Mixed_weight"] * (v_Mixed - r_Mixed) * 1e-3,
    }  # emissions data, daily savings
    ed_d = pd.DataFrame(ed_d).set_index("Date")
    ed_ds = pd.DataFrame(ed_ds).set_index("Date")
    # how do I get weekly - add up daily emissions.
    ed_w = ed_d.resample("W-MON").sum()
    ed_ws = ed_ds.resample("W-MON").sum()
    ed_m = ed_d.resample("MS").sum()
    ed_ms = ed_ds.resample("MS").sum()
    return df.set_index("Date"), ed_d, ed_w, ed_m, ed_ds, ed_ws, ed_ms


try:
    st.set_page_config(layout="wide")

    st.title("3D Printing Waste & Sustainability Analytics Dashboard")
    st.markdown("---")

    path = "data_500_days.csv"
    df, ed_d, ed_w, ed_m, ed_ds, ed_ws, ed_ms = get_data(
        path, os.path.getmtime(path)
    )
    students = df["num_students"]
    df = df.drop("num_students", axis=1)

    control_col, _ = st.columns([1, 2])
    with control_col:
        plastics = st.multiselect(
            "Choose Plastics", list(df.columns), default=["PLA_weight", "TPU_weight"]
        )

    if not plastics:
        st.error("Please select at least one bin's data you want to visualise")
    else:
        data = df[plastics]

        min_date = df.index.min()
        first_week_end = min_date + pd.Timedelta(days=7)
        domain_range = [
            min_date.strftime("%Y-%m-%d"),
            first_week_end.strftime("%Y-%m-%d"),
        ]

        col1, col2 = st.columns(2)

        with col1:
            st.header("Plastic collected over time ")
            chart = (
                alt.Chart(data.reset_index())
                .transform_fold(plastics, as_=["Plastic", "Weight"])
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Date:T",
                        title="Date",
                        scale=alt.Scale(domain=domain_range),
                        axis=alt.Axis(format="%b %d, %Y"),
                    ),
                    y=alt.Y("Weight:Q", title="Weight (g)"),
                    color="Plastic:N",
                    tooltip=["Date:T", "Plastic:N", "Weight:Q"],
                )
                .interactive(
                    bind_y=False
                )  # Allows X-axis scrolling/zooming, locks Y-axis
            )
            st.altair_chart(chart, use_container_width=True)

        with col2:
            # show Co2eq emissions per day, week and month given current usage
            # also show potential savings by recycling..
            st.header(
                "CO₂eq Emissions Over Time",
                help="""
                     Conveys the weight of carbon dioxide that produces the same global warming effects
                     as the gases released during the manufature, transport and packaging of a specific material.
                     """,
            )

            emissions_view = st.selectbox(
                "Period", ["Daily", "Weekly", "Monthly"], key="emissions_period"
            )

            emissions_data = {
                "Daily": ed_d,
                "Weekly": ed_w,
                "Monthly": ed_m,
            }[emissions_view]

            emissions_df = emissions_data.reset_index()

            emissions_chart = (
                alt.Chart(emissions_df)
                .transform_fold(
                    [
                        "PLA_emissions",
                        "PETG_emissions",
                        "TPU_emissions",
                        "Mixed_emissions",
                    ],
                    as_=["Plastic", "Emissions"],
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Date:T", title="Date", axis=alt.Axis(format="%b %d, %Y")
                    ),
                    y=alt.Y("Emissions:Q", title="CO₂eq Emissions (kg)"),
                    color=alt.Color("Plastic:N", title="Material"),
                    tooltip=[
                        alt.Tooltip("Date:T"),
                        alt.Tooltip("Plastic:N"),
                        alt.Tooltip(
                            "Emissions:Q", format=".3f", title="kg CO₂e"
                        ),
                    ],
                )
                .interactive(bind_y=False)
            )

            st.altair_chart(emissions_chart, use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            student_df = students.reset_index(name="Students")

            st.header("Number of students disposing waste over time")
            base_student_chart = alt.Chart(student_df).encode(
                x=alt.X(
                    "Date:T",
                    title="Date",
                    scale=alt.Scale(domain=domain_range),
                    axis=alt.Axis(format="%b %d, %Y"),
                ),
                y=alt.Y("Students:Q", title="Daily Participants"),
            )

            lines = base_student_chart.mark_bar(color="#1f77b4", strokeWidth=3)

            dots = base_student_chart.mark_circle(
                size=60, color="#1f77b4"
            ).encode(tooltip=["Date:T", "Students:Q"])
            combined_students = (lines + dots).interactive(bind_y=False)

            st.altair_chart(combined_students, use_container_width=True)

        with col4:
            st.header(
                "CO₂eq Savings Over Time",
                help="""
                     Emissions from recylcing subtracted from the cradle to gate emissions for a particular material 
                     """,
            )

            savings_view = st.selectbox(
                "Period", ["Daily", "Weekly", "Monthly"], key="savings_period"
            )

            savings_data = {
                "Daily": ed_ds,
                "Weekly": ed_ws,
                "Monthly": ed_ms,
            }[savings_view]

            savings_df = savings_data.reset_index()

            savings_chart = (
                alt.Chart(savings_df)
                .transform_fold(
                    [
                        "PLA_savings",
                        "PETG_savings",
                        "TPU_savings",
                        "Mixed_savings",
                    ],
                    as_=["Plastic", "Savings"],
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Date:T", title="Date", axis=alt.Axis(format="%b %d, %Y")
                    ),
                    y=alt.Y("Savings:Q", title="CO₂e Savings (kg)"),
                    color=alt.Color("Plastic:N", title="Material"),
                    tooltip=[
                        alt.Tooltip("Date:T"),
                        alt.Tooltip("Plastic:N"),
                        alt.Tooltip("Savings:Q", format=".3f", title="kg CO₂e"),
                    ],
                )
                .interactive(bind_y=False)
            )

            st.altair_chart(savings_chart, use_container_width=True)

except Exception as e:
    st.error(f"An error occurred: {e}") 