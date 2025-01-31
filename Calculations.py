# ----------------------- Utility Functions -----------------------#

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

# ----------------------- Calculation Functions -----------------------#

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