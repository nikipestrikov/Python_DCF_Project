# Green Area Calculation Rule
def green_area_formula(total_area: float) -> float:
    """
    Determine the green area percentage based on a given total area.
    Returns a percentage (0, 5, 10, 15, 17, or 18).
    """
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

# Calculation formula
def calculate_totals(plots: list,
                     apply_efficiency_incentive: bool,
                     green_allocation_method: str,
                     custom_green_allocations: list) -> dict:
    """
    Main calculation function that iterates over plots to determine
    net areas, road deductions, green deductions, buildable areas, etc.

    Returns a dictionary of consolidated results, including:
    total_net_area, total_road_deduction, total_green_deduction,
    commercial_buildable_area, residential_buildable_area, incentive_area,
    total_buildable_area, and updated plot data.
    """
    total_net_area = 0
    total_road_deduction = 0
    total_green_deduction = 0
    commercial_area = 0
    residential_area = 0
    commercial_density_sum = 0
    residential_density_sum = 0

    for i, plot in enumerate(plots):
        # Example logic for each plot:
        if plot["is_parceled"]:
            net_plot_size = plot["plot_size"]
            road_deduction = 0
            green_deduction = 0
        else:
            road_deduction = plot["plot_size"] * (plot["road_deduction_percent"] / 100)
            area_after_road = plot["plot_size"] - road_deduction
            green_percentage = green_area_formula(area_after_road)
            green_deduction = area_after_road * (green_percentage / 100)
            net_plot_size = area_after_road - green_deduction

        # Update plot dict
        plot["net_plot_size"] = net_plot_size
        plot["road_deduction"] = road_deduction
        plot["green_deduction"] = green_deduction

        # Accumulate totals
        total_net_area += net_plot_size
        total_road_deduction += road_deduction
        total_green_deduction += green_deduction

        # Zones logic
        plot["zone_buildable_areas"] = []
        for zone in plot["zones"]:
            zone_area = net_plot_size * (zone["percentage"] / 100)
            density_factor = zone["density_factor"]
            density_type = zone["density_type"].lower()

            # Accumulate commercial vs residential area
            if density_type == "commercial":
                commercial_area += zone_area
                commercial_density_sum += zone_area * density_factor
            else:
                residential_area += zone_area
                residential_density_sum += zone_area * density_factor

            buildable_area = (zone_area * density_factor) / 100
            plot["zone_buildable_areas"].append(round(buildable_area))

    # Compute average densities
    commercial_density_avg = (commercial_density_sum / commercial_area) if commercial_area else 0
    residential_density_avg = (residential_density_sum / residential_area) if residential_area else 0

    # Buildable areas
    commercial_buildable_area = (commercial_area * commercial_density_avg) / 100
    residential_buildable_area = (residential_area * residential_density_avg) / 100

    # Incentives (optional)
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
        "plots": plots,  # Return updated plots for further use
    }