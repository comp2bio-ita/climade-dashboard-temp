from Bio import Entrez
import ssl
import time
import logging

from dotenv import load_dotenv

from models.env_models import EnvSettings
from shared.utils.handlers import SeqHandler

load_dotenv()

settings = EnvSettings()

Entrez.email = settings.NCBI_EMAIL
Entrez.api_key = settings.NCBI_API_KEY

ssl._create_default_https_context = ssl._create_unverified_context

# Function to fetch sequences from GenBank
def fetch_sequences(accession_list, output_file="data/sequences/sequences.fasta") -> str:
    """Returns the output file path if succeed"""
    logger = logging.getLogger(__name__)

    with open(output_file, "w") as out_handle:
        for acc_id in accession_list:
            try:
                handle = Entrez.efetch(db="nucleotide", id=acc_id, rettype="fasta", retmode="text")

                seq_records = SeqHandler.parse_fasta(handle)

                # Write to output file
                for record in seq_records: 
                    SeqHandler.write_fasta_record(out_handle, record)

                handle.close()  

            except Exception as e:
                logger.error(f"Error fetching {acc_id}: {e}")

    logger.info(f"Sequences saved to {output_file}")
    return output_file

def fetch_sequences_batch(accession_list:list[str], batch_size=200, output_file="data/sequences/sequences.fasta", sleep_time:int = 0.1) -> str:
    logger = logging.getLogger(__name__)
    
    with open(output_file, "w") as out_handle:

        for i in range(0, len(accession_list), batch_size):

            batch_ids = accession_list[i:i + batch_size]

            try:
                handle = Entrez.efetch(db="nucleotide", id=",".join(batch_ids), rettype="fasta", retmode="text")

                seq_records = SeqHandler.parse_fasta(handle)

                # Write batch to output file
                for record in seq_records:
                    SeqHandler.write_fasta_record(out_handle, record)

                handle.close()  

                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error fetching batch {batch_ids}: {e}")

    logger.info(f"Sequences saved to {output_file}")
    return output_file
