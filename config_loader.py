import yaml
import os

class ConfigLoader:
    """
    Configuration loader to handle domain-specific settings.
    Ensures the agent can be easily ported to different domains (e.g., AIOps, Beauty, Stocks).
    """
    def __init__(self, config_dir="domain_configs"):
        self.config_dir = config_dir

    def load_config(self, domain_name: str):
        """
        Load YAML configuration based on the domain name.
        """
        file_path = os.path.join(self.config_dir, f"{domain_name.lower()}.yaml")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Domain configuration not found: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def list_available_domains(self):
        """
        List all supported domains currently available in the config directory.
        """
        return [f.split('.')[0] for f in os.listdir(self.config_dir) if f.endswith('.yaml')]

if __name__ == "__main__":
    # Simple test for verification
    loader = ConfigLoader()
    print(f"Supported domains: {loader.list_available_domains()}")
    aiops_config = loader.load_config("aiops")
    print(f"Loaded domain: {aiops_config['domain']}")