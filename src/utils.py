import os

def get_resource_path(*paths):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "..", "resources", *paths)