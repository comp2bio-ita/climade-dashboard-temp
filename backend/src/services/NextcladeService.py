import subprocess
import csv
from typing import Literal
import json
import logging

dataset_map = {
    "DENV1": "community/v-gen-lab/dengue/denv1",
    "DENV2": "community/v-gen-lab/dengue/denv2",
    "DENV3": "community/v-gen-lab/dengue/denv3",
    "DENV4": "community/v-gen-lab/dengue/denv4",
    "DENV-ALL-SEROTYPES": "nextstrain/dengue/all",
    "CHIKV": "community/v-gen-lab/chikV/genotypes",
    "YFV": "community/pathoplexus/yellow-fever-virus"
}

class NextcladeService:

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def run_nextclade(self, input_fasta_file_path: str, output_file_path: str, dataset: Literal["DENV-SEROTYPES", "DENV-1", "DENV-2", "DENV-3", "DENV-4"]):
        """
        Runs Nextclade CLI to process the given FASTA file. Returns a Json File path as output
        """

        try:
            # Run the Nextclade CLI command
            subprocess.run([
                # '/usr/local/bin/nextclade', 'run',
                'nextclade', 'run',
                "--jobs", "4",
                '-d', f'{dataset_map[dataset]}',        # Dataset folder (not --dataset)
                '-J', f'{output_file_path}',     # Output folder
                f'{input_fasta_file_path}'            # Positional argument for FASTA file
            ], check=True)
            self.logger.info(f"Nextclade analysis completed. Results saved to {output_file_path}")
            return output_file_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error running Nextclade: {e}")
            return None

    def parse_nextclade_csv(self, nextclade_csv) -> list[dict]:
        """
        Extracts serotype, genotype (or clade) information from Nextclade's CSV output.
        """
        clades = []
        try:
            with open(nextclade_csv, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    clade = row.get('clade', 'Unknown')
                    clades.append(dict(seq_name=row['seqName'], clade=clade))
                    
        except Exception as e:
            self.logger.error(f"Error reading CSV: {e}")

        return clades

    def parse_nextclade_json(self, json_file_path) -> list[dict]:
        """
        Converts Nextclade JSON output to a dictionary containing 'seqName' and 'clade'.
        
        Args:
        - json_file_path: The path to the Nextclade JSON output file.
        
        Returns:
        - A dictionary with 'seqName' as the key and 'clade' as the value.
        """
        # Open and load the JSON file
        with open(json_file_path, 'r') as f:
            nextclade_data = json.load(f)

        # Create a dictionary with 'seqName' as key and 'clade' as value
        results = []
        for item in nextclade_data["results"]:
            seq_name = item.get("seqName")
            clade = item.get("clade", "Unknown")
            results.append(dict(seq_name=seq_name, clade=clade))

        return results