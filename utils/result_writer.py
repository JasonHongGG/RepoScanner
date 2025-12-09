import csv
import json
import os
import logging
from config import OUTPUT_FORMAT

class ResultWriter:
    def __init__(self, output_format=OUTPUT_FORMAT):
        self.output_format = output_format.lower()
        self.logger = logging.getLogger(__name__)

    def save(self, results, filename):
        """
        Saves results to the specified filename.
        Delegates to specific format handlers based on self.output_format.
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        if self.output_format == 'json':
            self._save_json(results, filename)
        else:
            self._save_csv(results, filename)

    def _save_csv(self, results, filename):
        file_exists = os.path.isfile(filename)
        try:
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["repo", "type", "value", "commit", "location", "file_url"], extrasaction='ignore')
                if not file_exists:
                    writer.writeheader()
                
                for r in results:
                    writer.writerow(r)
        except Exception as e:
            self.logger.error(f"Failed to save CSV results to {filename}: {e}")

    def _save_json(self, results, filename):
        current_data = []
        if os.path.isfile(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    current_data = json.load(f)
            except json.JSONDecodeError:
                pass # Start fresh if corrupt
                
        current_data.extend(results)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save JSON results to {filename}: {e}")
