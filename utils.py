import json

def save_configuration(config_data, file_name="config.json"):
    """Save the given configuration dictionary to a file."""
    with open(file_name, "w") as file:
        json.dump(config_data, file, indent=4)

def load_configuration(file_name="config.json"):
    """Load configuration from a file."""
    try:
        with open(file_name, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None