from fpdf import FPDF
from io import BytesIO
import pandas as pd
import tempfile
import os

# ----------------------- PDF Report Generator -----------------------#
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

    # Add Total Price
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(0, 10, f"Total Project Price: EUR {total_price:,.2f}", ln=True, align="C")  # Adding project price
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
    total_plot_size = 0
    total_road_deduction = 0
    total_green_deduction = 0
    total_net_land_area = 0

    for i, plot in enumerate(results["plots"]):
        plot_size = round(plot['plot_size'])
        road_deduction = round(plot['road_deduction'])
        green_deduction = round(plot['green_deduction'])
        net_land_area = round(plot['net_plot_size'])

        row = [
            f"Plot {i + 1}",
            f"{plot_size:,}",
            f"{road_deduction:,}",
            f"{green_deduction:,}",
            f"{net_land_area:,}",
        ]
        total_plot_size += plot_size
        total_road_deduction += road_deduction
        total_green_deduction += green_deduction
        total_net_land_area += net_land_area

        for data, width in zip(row, col_widths):
            pdf.cell(width, 10, data, border=1, align="C")
        pdf.ln()

        # Add a Total Row
        pdf.set_font("Arial", style="B", size=10)  # Bold font for the total row
        total_row = [
            "Total",
            f"{total_plot_size:,}",
            f"{total_road_deduction:,}",
            f"{total_green_deduction:,}",
            f"{total_net_land_area:,}",
        ]
        for data, width in zip(total_row, col_widths):
            pdf.cell(width, 10, data, border=1, align="C")
        pdf.ln()

        pdf.ln(10)

    # Save PDF to a temporary file in a cross-platform way
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, 'report.pdf')
    pdf.output(temp_file)

    # Read the file into a BytesIO object
    with open(temp_file, "rb") as f:
        pdf_data = BytesIO(f.read())
    return pdf_data

# ----------------------- Excel Report Generator -----------------------#


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