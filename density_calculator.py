import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

# Function to calculate net land area based on plot type
def calculate_net_land_area(plot_size, is_parceled, road_deduction_percent, green_deduction):
    if is_parceled:
        return plot_size, 0, green_deduction
    else:
        road_deduction = plot_size * (road_deduction_percent / 100)
        net_area = plot_size - road_deduction - green_deduction
        return round(net_area), round(road_deduction), round(green_deduction)

# Green area deduction based on total combined plot size
def green_area_formula(total_area):
    if total_area < 800:
        return 0
    elif 800 <= total_area < 1500:
        return total_area * 0.05
    elif 1500 <= total_area < 2500:
        return total_area * 0.10
    elif 2500 <= total_area < 10000:
        return total_area * 0.15
    elif 10000 <= total_area < 50000:
        return total_area * 0.17
    else:
        return total_area * 0.18

# Function to calculate totals and handle green area allocation
def calculate_totals(plots, apply_efficiency_incentive, green_allocation_method, custom_green_allocations):
    total_plot_size = sum(plot["plot_size"] for plot in plots)
    total_net_area = 0
    total_road_deduction = 0
    total_green_deduction = 0
    commercial_area = 0
    residential_area = 0
    commercial_density_sum = 0
    residential_density_sum = 0

    # Calculate total green area deduction
    total_green_area = green_area_formula(total_plot_size)

    # Allocate green area to each plot
    if green_allocation_method == "Proportional":
        for plot in plots:
            plot["allocated_green"] = min(total_green_area * (plot["plot_size"] / total_plot_size), plot["plot_size"])
    elif green_allocation_method == "Custom":
        total_custom_allocation = sum(custom_green_allocations)
        for i, plot in enumerate(plots):
            plot["allocated_green"] = min(total_green_area * (custom_green_allocations[i] / total_custom_allocation), plot["plot_size"])

    # Calculate net areas and densities
    for plot in plots:
        green_deduction = plot.get("allocated_green", 0)
        net_plot_size, road_deduction, green_deduction = calculate_net_land_area(
            plot["plot_size"],
            plot["is_parceled"],
            plot["road_deduction_percent"],
            green_deduction
        )
        plot["net_plot_size"] = net_plot_size
        plot["road_deduction"] = road_deduction
        plot["green_deduction"] = green_deduction

        total_net_area += net_plot_size
        total_road_deduction += road_deduction
        total_green_deduction += green_deduction

        plot["zone_buildable_areas"] = []
        for zone in plot["zones"]:
            zone_area = net_plot_size * (zone["percentage"] / 100)
            density_factor = zone["density_factor"]
            density_type = zone["density_type"].lower()

            if density_type == "commercial":
                commercial_area += zone_area
                commercial_density_sum += zone_area * density_factor
            elif density_type == "residential":
                residential_area += zone_area
                residential_density_sum += zone_area * density_factor

            buildable_area = (zone_area * density_factor) / 100
            plot["zone_buildable_areas"].append(round(buildable_area))

    commercial_density_avg = (commercial_density_sum / commercial_area) if commercial_area else 0
    residential_density_avg = (residential_density_sum / residential_area) if residential_area else 0

    commercial_buildable_area = (commercial_area * commercial_density_avg) / 100
    residential_buildable_area = (residential_area * residential_density_avg) / 100

    incentive_area = 0
    if apply_efficiency_incentive:
        incentive_area = 0.05 * (commercial_buildable_area + residential_buildable_area)

    total_buildable_area = commercial_buildable_area + residential_buildable_area + incentive_area

    return {
        "total_net_area": round(total_net_area),
        "total_road_deduction": round(total_road_deduction),
        "total_green_deduction": round(total_green_deduction),
        "commercial_avg_density": round(commercial_density_avg),
        "residential_avg_density": round(residential_density_avg),
        "commercial_buildable_area": round(commercial_buildable_area),
        "residential_buildable_area": round(residential_buildable_area),
        "incentive_area": round(incentive_area),
        "total_buildable_area": round(total_buildable_area),
        "plots": plots
    }

# Streamlit UI
st.title("Real Estate Density Calculator")

st.sidebar.header("Plot Configuration")
num_plots = st.sidebar.number_input("Number of Plots", min_value=1, max_value=10, value=1, step=1)

apply_efficiency_incentive = st.sidebar.checkbox("Apply 5% Efficiency Incentive")
price_toggle = st.sidebar.radio("Specify Price For", ["Each Plot", "Total Project"])

green_allocation_method = st.sidebar.radio("Public Green Allocation Method", ["Proportional", "Custom"])
custom_green_allocations = []

total_price = 0
plots = []

if price_toggle == "Total Project":
    total_price = st.number_input("Total Project Price (€)", min_value=0, step=1, format="%d")

for i in range(num_plots):
    with st.sidebar.expander(f"Plot {i + 1} Configuration", expanded=False):
        serial_number = st.text_input(f"Plot {i + 1} Serial Number", value=f"Plot-{i + 1}", key=f"serial_{i}")
        plot_size = st.number_input(f"Plot {i + 1} Size (m²)", min_value=0, value=1000, step=1, format="%d", key=f"plot_size_{i}")
        is_parceled = st.checkbox(f"Is Plot {i + 1} Parceled?", value=True, key=f"parceled_{i}")
        road_deduction_percent = 0

        if not is_parceled:
            road_deduction_percent = st.slider(f"Plot {i + 1} Road Deduction (%)", min_value=0, max_value=50, value=10, step=1, key=f"road_{i}")

        num_zones = st.number_input(f"Number of Zones", min_value=1, max_value=3, value=1, step=1, key=f"zones_{i}")
        zones = []
        remaining_percentage = 100

        for j in range(int(num_zones)):
            percentage = st.slider(f"Zone {j + 1} %", min_value=0, max_value=remaining_percentage, value=remaining_percentage, step=1, key=f"zone_{i}_{j}")
            remaining_percentage -= percentage
            density_factor = st.number_input(f"Zone {j + 1} Density Factor (%)", min_value=0, value=50, step=1, key=f"density_{i}_{j}")
            density_type = st.selectbox(f"Zone {j + 1} Type", ["Residential", "Commercial"], key=f"type_{i}_{j}")
            zones.append({"percentage": percentage, "density_factor": density_factor, "density_type": density_type})

        plot_price = st.number_input(f"Price for Plot {i + 1}", min_value=0, step=1, format="%d", key=f"price_{i}") if price_toggle == "Each Plot" else 0
        total_price += plot_price

        plots.append({"serial_number": serial_number, "plot_size": plot_size, "is_parceled": is_parceled, "road_deduction_percent": road_deduction_percent, "zones": zones})

if green_allocation_method == "Custom":
    st.sidebar.header("Custom Green Area Allocation")
    allocated_sum = 0

    for i in range(num_plots):
        max_allocation = 100 - allocated_sum
        max_allocation = min(max_allocation, int(plots[i]["plot_size"] / green_area_formula(sum(p["plot_size"] for p in plots)) * 100))
        allocation = st.sidebar.slider(
            f"Green Allocation for Plot {i + 1} (%)",
            min_value=0,
            max_value=max_allocation,
            value=min(100 // num_plots, max_allocation),
            step=1,
            key=f"custom_green_{i}"
        )
        allocated_sum += allocation
        custom_green_allocations.append(allocation)

#Excel Generate Function
def generate_excel_report(results, total_price, price_per_m2):
    output = BytesIO()

    # Create main summary DataFrame
    summary_data = {
        "Metric": [
            "Total Buildable Area (m²)",
            "Residential Buildable Area (m²)",
            "Commercial Buildable Area (m²)",
            "Total Deductions (m²)",
            "Road Deduction (m²)",
            "Public Green Deduction (m²)",
            "Price per Buildable Area (€)",
        ],
        "Value": [
            results['total_buildable_area'],
            results['residential_buildable_area'],
            results['commercial_buildable_area'],
            results['total_road_deduction'] + results['total_green_deduction'],
            results['total_road_deduction'],
            results['total_green_deduction'],
            f"{price_per_m2:,.2f}",
        ]
    }
    summary_df = pd.DataFrame(summary_data)

    # Create detailed plot breakdown
    plot_details = []
    for plot in results['plots']:
        for j, zone_buildable_area in enumerate(plot["zone_buildable_areas"]):
            zone = plot["zones"][j]
            plot_details.append({
                "Plot Serial Number": plot["serial_number"],
                "Plot Area (m²)": plot["plot_size"],
                "Road Deduction (m²)": plot["road_deduction"],
                "Public Green Deduction (m²)": plot["green_deduction"],
                "Net Land Area (m²)": plot["net_plot_size"],
                "Zone": f"Zone {j + 1}",
                "Zone Percentage (%)": zone["percentage"],
                "Density Factor (%)": zone["density_factor"],
                "Zone Type": zone["density_type"],
                "Buildable Area (m²)": zone_buildable_area,
            })

    plot_df = pd.DataFrame(plot_details)

    # Write both DataFrames to Excel
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        plot_df.to_excel(writer, index=False, sheet_name="Plot Details")

    output.seek(0)
    return output

# Function to generate a detailed PDF report
class PDF(FPDF):
    def output_to_bytes(self):
        # Create a BytesIO stream for storing the PDF data in memory
        pdf_output = BytesIO()
        # We override the output method to accept a file-like object (like BytesIO)
        self.output(pdf_output)  # Write the PDF to the BytesIO object
        pdf_output.seek(0)  # Go to the beginning of the BytesIO stream
        return pdf_output.getvalue()  # Return the PDF data as bytes

def generate_pdf_report(results, total_price, price_per_m2):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add Title
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(0, 10, "Real Estate Density Calculation Report", ln=True, align="C")
    pdf.ln(10)

    # Summary Section
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(0, 10, "Summary", ln=True)
    pdf.set_font("Arial", size=12)

    summary_data = [
        f"Total Buildable Area (m²): {results['total_buildable_area']:,}",
        f"Residential Buildable Area (m²): {results['residential_buildable_area']:,}",
        f"Commercial Buildable Area (m²): {results['commercial_buildable_area']:,}",
        f"Total Deductions (m²): {results['total_road_deduction'] + results['total_green_deduction']:,}",
        f"Road Deduction (m²): {results['total_road_deduction']:,}",
        f"Public Green Deduction (m²): {results['total_green_deduction']:,}",
        f"Price per Buildable Area (EURO): {price_per_m2:,.2f}",
    ]
    for line in summary_data:
        pdf.cell(0, 10, line, ln=True)

    pdf.ln(10)

    # Detailed Breakdown for Each Plot
    pdf.set_font("Arial", style="B", size="14")
    pdf.cell(0, 10, "Detailed Plot Breakdown", ln=True)
    pdf.set_font("Arial", size=12)

    for i, plot in enumerate(results['plots']):
        pdf.ln(5)
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(0, 10, f"Plot {i + 1} ({plot['serial_number']})", ln=True)
        pdf.set_font("Arial", size=12)

        plot_data = [
            f"Plot Area (m²): {plot['plot_size']:,}",
            f"Road Deduction (m²): {plot['road_deduction']:,}",
            f"Public Green Allocated (m²): {plot['green_deduction']:,}",
            f"Net Land Area (m²): {plot['net_plot_size']:,}",
        ]
        for line in plot_data:
            pdf.cell(0, 10, line, ln=True)

        for j, zone_buildable_area in enumerate(plot["zone_buildable_areas"]):
            zone = plot["zones"][j]
            pdf.cell(
                0,
                10,
                f"Zone {j + 1}: {zone['percentage']}% | "
                f"Density Factor: {zone['density_factor']}% | "
                f"Type: {zone['density_type']} | "
                f"Buildable Area (m²): {zone_buildable_area:,}",
                ln=True,
            )

    # Generate the PDF as binary data in memory
    pdf_data = pdf.output_to_bytes()

    return pdf_data

if st.button("Calculate"):
    results = calculate_totals(plots, apply_efficiency_incentive, green_allocation_method, custom_green_allocations)
    price_per_m2 = total_price / results['total_buildable_area'] if results['total_buildable_area'] else 0

    # Highlighted Statistics
    st.markdown(
        f"<div style='background-color:#d4edda;padding:10px;border-radius:5px;margin-bottom:10px;'>" +
        f"<b>Price per Buildable Area:</b> €{price_per_m2:,.0f}/m²</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<div style='background-color:#fff3cd;padding:10px;border-radius:5px;margin-bottom:10px;'>" +
        f"<b>Total Buildable Area:</b> {results['total_buildable_area']:,} m² " +
        f"<details><summary>Click to expand</summary>" +
        f"Residential: {results['residential_buildable_area']:,} m²<br>" +
        f"Commercial: {results['commercial_buildable_area']:,} m²" +
        f"</details></div>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<div style='background-color:#f8d7da;padding:10px;border-radius:5px;margin-bottom:10px;'>" +
        f"<b>Total Deductions:</b> {results['total_road_deduction'] + results['total_green_deduction']:,} m² " +
        f"<details><summary>Click to expand</summary>" +
        f"Road: {results['total_road_deduction']:,} m²<br>" +
        f"Public Green: {results['total_green_deduction']:,} m²" +
        f"</details></div>",
        unsafe_allow_html=True
    )

    # Excel Export
    excel_data = generate_excel_report(results, total_price, price_per_m2)
    st.download_button(
        label="Download Excel Report",
        data=excel_data,
        file_name="density_calculation_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # PDF Export
    pdf_data = generate_pdf_report(results, total_price, price_per_m2)
    st.download_button(
        label="Download PDF Report",
        data=pdf_data,
        file_name="density_calculation_results.pdf",
        mime="application/pdf"
    )
    # Detailed Breakdown for Each Plot
    st.subheader("Detailed Calculation Breakdown")
    for i, plot in enumerate(results['plots']):
        with st.expander(f"Plot {i + 1} ({plot['serial_number']})"):
            st.markdown(f"**Plot Area:** {plot['plot_size']:,} m²")
            st.markdown(f"**Road Deduction:** {plot['road_deduction']:,} m²")
            st.markdown(f"**Public Green Allocated:** {plot['green_deduction']:,} m²")
            st.markdown(f"**Net Land Area:** {plot['net_plot_size']:,} m²")

            for j, zone_buildable_area in enumerate(plot["zone_buildable_areas"]):
                zone = plot["zones"][j]
                st.markdown(
                    f"**Zone {j + 1}:** {zone['percentage']}% | Density Factor: {zone['density_factor']}% | " +
                    f"Type: {zone['density_type']} | Buildable Area: {zone_buildable_area:,} m²"
                )
