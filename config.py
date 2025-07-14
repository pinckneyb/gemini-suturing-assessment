import os
import json
from pathlib import Path

class Config:
    def __init__(self):
        self.config_file = Path("suturing_assessment_config.json")
        self.api_key = ""
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.api_key = data.get('api_key', '')
            except Exception as e:
                print(f"Error loading config: {e}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            data = {
                'api_key': self.api_key
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def set_api_key(self, api_key):
        """Set API key and save to config"""
        self.api_key = api_key
        self.save_config()
    
    def get_api_key(self):
        """Get API key"""
        return self.api_key 