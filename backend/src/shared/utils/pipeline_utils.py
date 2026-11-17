from dotenv import load_dotenv
from shared.scripts.fetchSequenceFastaFromGenbank import fetch_sequences, fetch_sequences_batch
from models.database_models import ChikungunyaMetaEntity, ZikaMetaEntity
from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService
import logging

import pandas as pd

def main():

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    load_dotenv()

    settings = EnvSettings()

    logger = logging.getLogger(__name__)

    database_service  = DatabaseService(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        database=settings.DASH_DATABASE,
        user=settings.DASH_USER,
        password=settings.DASH_PASSWORD
    )

    zika_outstanding = database_service.get_record_by_filters(
        entity_class=ZikaMetaEntity,
        and_filters=[ZikaMetaEntity.genotype.is_(None)]
    )

    print()
    print(len(zika_outstanding))
    print()

    chikunguniaOutstanding = database_service.get_record_by_filters(
        entity_class=ChikungunyaMetaEntity,
        and_filters=[ChikungunyaMetaEntity.genotype.is_(None)]
    )

    print()
    print(len(chikunguniaOutstanding))
    print()

    zika_accessions = [ item["genbank_sequence_data_id"] for item in zika_outstanding ] if zika_outstanding else []

    chik_accessions = [ item["genbank_sequence_data_id"] for item in chikunguniaOutstanding ] if chikunguniaOutstanding else []

    if zika_accessions:
        fetch_sequences_batch(
            accession_list=zika_accessions,
            output_file="data/sequences/zika_outstanding_sequences.fasta"
        )

    if chik_accessions:
        fetch_sequences_batch(
            accession_list=chik_accessions,
            output_file="data/sequences/chikv_outstanding_sequences.fasta"
        )

    print("Finished")
    
    
if __name__=="__main__":
    main()