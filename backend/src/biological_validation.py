# This script is used to validate the biological sequences using the NCBI API isolated from the pipeline

from Bio import Entrez
from models.env_models import EnvSettings
from dotenv import load_dotenv
from shared.utils.handlers import SeqHandler

load_dotenv()

settings = EnvSettings()

Entrez.email = settings.NCBI_EMAIL
Entrez.api_key = settings.NCBI_API_KEY

ids = ["AB519681.1", "AF425614.1"]

handle = Entrez.efetch(
    db="nucleotide",
    id=",".join(ids),
    rettype="fasta",
    retmode="text"
)

# records = list(SeqIO.parse(handle, "fasta"))
recortds = SeqHandler.parse_fasta(handle)

# SeqIO.write(records, "test.fasta", "fasta")
SeqHandler.write_fasta(recortds, "test.fasta", line_width=150)

handle.close()