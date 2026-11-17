import gc
import logging
from services.DatabaseService import DatabaseService
from shared.scripts.fetchSequenceFastaFromGenbank import fetch_sequences_batch
from models.database_models import ChikungunyaMetaEntity


def chikGenotypeRecognizer(database_service: DatabaseService) -> None:
    from services.NextcladeService import NextcladeService

    logger = logging.getLogger(__name__)

    logger.info("Initializing Genotypes Recognition")

    output_sequences_file = "data/sequences/output_sequences.fasta"
    output_nextclade = "data/classification/output_nextclade.json"

    logger.info("Fetching unclassified data from climade database")

    updated_records = []

    unclassified = database_service.get_record_by_filters(
        entity_class=ChikungunyaMetaEntity,
        and_filters=[
            ChikungunyaMetaEntity.genotype.is_(None), 
            ChikungunyaMetaEntity.length >=1000
        ] 
    ) 

    if not unclassified:
        logger.info(f"There is no unclassified data for serotype CHIKV")
        return

    accession_list = [ item["genbank_sequence_data_id"] for item in unclassified ]

    logger.info(f"{len(accession_list)} unclassified CHIKV sequencens found in the database")

    nexclade_batch_size = 300

    for i in range(0, len(accession_list), nexclade_batch_size):

        batch_ids = accession_list[i:i + nexclade_batch_size]

        logger.info(f"Fetching CHIKV sequences from Entrez")

        output_sequences = fetch_sequences_batch(accession_list=batch_ids, output_file=output_sequences_file)

        logger.info("Running nextclade to get classifications")

        nexcladeService = NextcladeService()

        nextclade_output = nexcladeService.run_nextclade(
            input_fasta_file_path=output_sequences,
            output_file_path=output_nextclade,
            dataset="CHIKV"
        )

        nexclade_results = nexcladeService.parse_nextclade_json(nextclade_output)

        if not nexclade_results:
            logger.info("Unable to find classifications via nextclade")
            continue

        logger.info("Updating database records")

        for item_result in nexclade_results:
            for database_item in unclassified:
                if database_item["genbank_sequence_data_id"] in item_result["seq_name"]:

                    clade = item_result.get("clade")

                    if not clade:
                        continue

                    splitted_clade = clade.split("-")

                    genotype = splitted_clade[1] if splitted_clade else None

                    database_item["genotype"] = genotype

                    updated_records.append(database_item)
                    break
        del batch_ids
        del output_sequences
        del nextclade_output
        del nexclade_results
        gc.collect()

    database_service.update_bulk(entity_class=ChikungunyaMetaEntity, records=updated_records)

    logger.info("Finished")