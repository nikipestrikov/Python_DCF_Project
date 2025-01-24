import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

# Function to calculate net land area based on plot type
def calculate_net_land_area(plot_size, is_parceled, road_deduction_percent, green_percentage):
    if is_parceled:
        # If parceled, no road or green deductions apply
        return plot_size, 0, 0
    else:
        # Calculate road deduction
        road_deduction = plot_size * (road_deduction_percent / 100)
        area_after_road = plot_size - road_deduction

        # Calculate green deduction on the area remaining after road deduction
        green_deduction = area_after_road * (green_percentage / 100)

        # Calculate net area
        net_area = area_after_road - green_deduction

        return round(net_area), round(road_deduction), round(green_deduction)

# Green area deduction based on total combined plot size
def green_area_formula(total_area):
    if total_area < 800:
        return 0
    elif 800 <= total_area < 1500:
        return 5
    elif 1500 <= total_area < 2500:
        return 10
    elif 2500 <= total_area < 10000:
        return 15
    elif 10000 <= total_area < 50000:
        return 17
    else:
        return 18

# Function to calculate totals and handle green area allocation
def calculate_totals(plots, apply_efficiency_incentive, green_allocation_method, custom_green_allocations):
    total_net_area = 0
    total_road_deduction = 0
    total_green_deduction = 0
    commercial_area = 0
    residential_area = 0
    commercial_density_sum = 0
    residential_density_sum = 0

    for plot in plots:
        if plot["is_parceled"]:
            # For parceled plots, no deductions apply
            plot["net_plot_size"] = plot["plot_size"]
            plot["road_deduction"] = 0
            plot["green_deduction"] = 0
        else:
            # Calculate road deduction
            road_deduction = plot["plot_size"] * (plot["road_deduction_percent"] / 100)
            area_after_road = plot["plot_size"] - road_deduction

            # Recalculate green percentage based on area after road deduction
            green_percentage = green_area_formula(area_after_road)
            green_deduction = area_after_road * (green_percentage / 100)

            # Calculate net area
            net_plot_size = area_after_road - green_deduction

            # Update plot values
            plot["net_plot_size"] = net_plot_size
            plot["road_deduction"] = road_deduction
            plot["green_deduction"] = green_deduction

            # Update totals
            total_net_area += net_plot_size
            total_road_deduction += road_deduction
            total_green_deduction += green_deduction

        # Calculate buildable area by zones
        plot["zone_buildable_areas"] = []
        for zone in plot["zones"]:
            zone_area = plot["net_plot_size"] * (zone["percentage"] / 100)
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
st.sidebar.image("logo.png", width=75)
st.markdown("<h1 style='text-align: center;'>Project Density Analysis</h1>", unsafe_allow_html=True)

st.sidebar.header("Plot Configuration")
num_plots = st.sidebar.number_input("Number of Plots", min_value=1, max_value=10, value=1, step=1)

project_name = st.sidebar.text_input("Project Name", value="My Real Estate Project")

apply_efficiency_incentive = st.sidebar.checkbox("Apply 5% Efficiency Incentive")
price_toggle = st.sidebar.radio("Specify Price For", ["Each Plot", "Total Project"])

green_allocation_method = st.sidebar.radio("Public Green Allocation Method", ["Proportional", "Custom"])
custom_green_allocations = []

total_price = 0
plots = []

if price_toggle == "Total Project":
    total_price_input = st.text_input("Total Project Price (€)", value="100,000")
    try:
        total_price = int(total_price_input.replace(",", ""))  # Remove commas and convert to integer
        if total_price < 0:
            st.error("Total project price must be a positive number.")
            total_price = 0
        else:
            # Re-display the value with commas
            total_price_input = f"{total_price:,}"
    except ValueError:
        st.error("Please enter a valid number for total project price.")
        total_price = 0

for i in range(num_plots):
    with st.sidebar.expander(f"Plot {i + 1} Configuration", expanded=False):
        serial_number = st.text_input(f"Plot {i + 1} Serial Number", value=f"Plot-{i + 1}", key=f"serial_{i}")
        plot_size_input = st.text_input(f"Plot {i + 1} Size (m²)", value="1,000", key=f"plot_size_{i}")
        try:
            plot_size = int(plot_size_input.replace(",", ""))  # Remove commas and convert to integer
            if plot_size < 0:
                st.error("Plot size must be a positive number.")
                plot_size = 0
            else:
                # Re-display the value with commas
                plot_size_input = f"{plot_size:,}"
        except ValueError:
            st.error("Please enter a valid number for plot size.")
            plot_size = 0
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
def generate_pdf_report(results, total_price, price_per_m2, project_name):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Add Logo
    logo_path = "logo.png"  # Ensure this is the correct path to your logo
    pdf.image(logo_path, x=10, y=8, w=30)  # Adjust the position and size as needed

    # Add Title and Project Name
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(0, 10, "Density Analysis Report", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(0, 10, f"Project: {project_name}", ln=True, align="C")
    pdf.ln(10)

    # Summary Section
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(0, 10, "Summary", ln=True)
    pdf.set_font("Arial", size=12)

    summary_data = [
        f"Total Buildable Area: {round(results['total_buildable_area']):,} m²",
        f"Residential Buildable Area: {round(results['residential_buildable_area']):,} m²",
        f"Commercial Buildable Area: {round(results['commercial_buildable_area']):,} m²",
        f"Total Deductions: {round(results['total_road_deduction'] + results['total_green_deduction']):,} m²",
        f"Price per Buildable Area: EUR {round(price_per_m2):,}",
    ]
    for line in summary_data:
        pdf.cell(0, 10, line, ln=True)

    pdf.ln(10)

    # Detailed Plot Breakdown in a Table
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(0, 10, "Detailed Plot Breakdown", ln=True)
    pdf.ln(5)

    # Define Table Column Headers with Shrinking Font
    pdf.set_font("Arial", style="B", size=10)  # Smaller font for headers
    headers = ["Plot", "Plot Size (m²)", "Road Deduction (m²)", "Green Deduction (m²)", "Net Land Area (m²)"]
    col_widths = [30, 40, 40, 40, 40]  # Adjust column widths as needed

    for header, width in zip(headers, col_widths):
        pdf.cell(width, 10, header, border=1, align="C")
    pdf.ln()

    # Populate Table with Data
    pdf.set_font("Arial", size=10)  # Match font size to headers
    for i, plot in enumerate(results["plots"]):
        row = [
            f"Plot {i + 1}",
            f"{round(plot['plot_size']):,}",
            f"{round(plot['road_deduction']):,}",
            f"{round(plot['green_deduction']):,}",
            f"{round(plot['net_plot_size']):,}",
        ]
        for data, width in zip(row, col_widths):
            pdf.cell(width, 10, data, border=1, align="C")
        pdf.ln()

    pdf.ln(10)

    # Save PDF to a temporary file
    temp_file = "/tmp/report.pdf"
    pdf.output(temp_file)

    # Read the file into a BytesIO object
    with open(temp_file, "rb") as f:
        pdf_data = BytesIO(f.read())
    return pdf_data

# Calculate button with session state handling
if st.button("Calculate"):
    # Perform calculations
    results = calculate_totals(plots, apply_efficiency_incentive, green_allocation_method, custom_green_allocations)
    price_per_m2 = total_price / results['total_buildable_area'] if results['total_buildable_area'] else 0

    # Store results in session state
    st.session_state["results"] = results
    st.session_state["price_per_m2"] = price_per_m2
    st.session_state["total_price"] = total_price
    st.session_state["calculated"] = True  # Set a flag to indicate that calculations have been performed

# Check if calculations exist in session state
if "calculated" in st.session_state and st.session_state["calculated"]:
    results = st.session_state["results"]
    price_per_m2 = st.session_state["price_per_m2"]
    total_price = st.session_state["total_price"]

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
    try:
        pdf_data = generate_pdf_report(results, total_price, price_per_m2, project_name)
        st.download_button(
            label="Download PDF Report",
            data=pdf_data,
            file_name="density_calculation_results.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Failed to generate PDF: {e}")

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
