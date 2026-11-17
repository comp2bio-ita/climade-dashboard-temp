from models.database_models import DengueMetaEntity
from services.DatabaseService import DatabaseService
from shared.scripts.fetchSequenceFastaFromGenbank import fetch_sequences_batch
import logging
import gc


def dengueSerotypeRecognizer(database_service: DatabaseService) -> None:
    from services.NextcladeService import NextcladeService

    logger = logging.getLogger(__name__)

    logger.info("Initializing Serotypes Recognition")

    output_sequences_file = "data/sequences/output_sequences.fasta"
    output_nextclade = "data/classification/output_nextclade.json"

    logger.info("Fetching unclassified data from climade database")

    unclassified_serotypes = database_service.get_record_by_filters(
        entity_class=DengueMetaEntity,
        and_filters=[DengueMetaEntity.serotype.is_(None), DengueMetaEntity.length >=1000] ## nextclade only works for sequences bigger than 1000
    ) 

    logger.info(f"{len(unclassified_serotypes)} unclassified serotypes")

    if not unclassified_serotypes:
        logger.info("There is no unclassified data in the database")
        return

    accession_list = [ item["genbank_sequence_data_id"] for item in unclassified_serotypes ]

    nexclade_batch_size = 300

    for i in range(0, len(accession_list), nexclade_batch_size):

        batch_ids = accession_list[i:i + nexclade_batch_size]

        logger.info("Fetching sequence data from Entrez")

        output_sequences = fetch_sequences_batch(accession_list=batch_ids, batch_size=200,output_file=output_sequences_file)

        logger.info("Running nextclade to get classifications")

        nexcladeService = NextcladeService()

        try:
            nextclade_output = nexcladeService.run_nextclade(
                input_fasta_file_path=output_sequences,
                output_file_path=output_nextclade,
                dataset="DENV-ALL-SEROTYPES"
            )
        except Exception as e:
            logger.error(f"Error running Nextclade:\n\n {e}")
            continue

        nexclade_results = nexcladeService.parse_nextclade_json(nextclade_output)

        logger.info("Updating database records")

        if not nexclade_results:
            continue

        target_records = []
      
        for classification in nexclade_results:
            for item in unclassified_serotypes:
                if item["genbank_sequence_data_id"] in classification["seq_name"]:
                    item["serotype"] = classification["clade"]
                    target_records.append(item)
                    break

        if target_records:
            logger.info("Database Commit")
            database_service.update_bulk(entity_class=DengueMetaEntity, records=target_records)

        logger.info("Batch Finished")

        del batch_ids
        del output_sequences
        del nextclade_output
        del nexclade_results
        del target_records
        gc.collect()

    logger.info("Finished All")



def dengueGenotypeRecognizer(database_service: DatabaseService) -> None:
    from services.NextcladeService import NextcladeService

    logger = logging.getLogger(__name__)

    logger.info("Initializing Genotypes Recognition")

    output_sequences_file = "data/sequences/output_sequences.fasta"
    output_nextclade = "data/classification/output_nextclade.json"

    logger.info("Fetching unclassified data from climade database")

    updated_records = []

    for seortype in ["DENV1", "DENV2", "DENV3", "DENV4"]:

        logger.info(f"Classifying {seortype}")

        # unclassified = [item for item in results if item["serotype"] == seortype and not item["genotype"]]

        unclassified = database_service.get_record_by_filters(
            entity_class=DengueMetaEntity,
            and_filters=[
                DengueMetaEntity.serotype == seortype, 
                DengueMetaEntity.genotype.is_(None), 
                DengueMetaEntity.length >=1000
            ] ## nextclade only works for sequences bigger than 1000
        ) 

        if not unclassified:
            logger.info(f"There is no unclassified data for serotype {seortype}")
            continue

        accession_list = [ item["genbank_sequence_data_id"] for item in unclassified ]

        nexclade_batch_size = 300

        for i in range(0, len(accession_list), nexclade_batch_size):

            batch_ids = accession_list[i:i + nexclade_batch_size]

            logger.info(f"Fetching {seortype} sequences from Entrez")

            output_sequences = fetch_sequences_batch(accession_list=batch_ids, output_file=output_sequences_file)

            logger.info("Running nextclade to get classifications")

            nexcladeService = NextcladeService()

            nextclade_output = nexcladeService.run_nextclade(
                input_fasta_file_path=output_sequences,
                output_file_path=output_nextclade,
                dataset=seortype
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

                        splitted_clade = clade.split("_")
                        lineage_parts = clade.split(".")

                        genotype = splitted_clade[0] if splitted_clade else None
                        major_lineage = lineage_parts[0] if lineage_parts else None
                        minor_lineage = clade if len(lineage_parts) > 1 else None

                        database_item["genotype"] = genotype
                        database_item["major_lineage"] = major_lineage if major_lineage != genotype else None
                        database_item["minor_lineage"] = minor_lineage

                        # parsed_records = [ DengueMetaEntity(**database_item) for database_item in unclassified ]
                        updated_records.append(database_item)
                        break
            del batch_ids
            del output_sequences
            del nextclade_output
            del nexclade_results
            gc.collect()

    database_service.update_bulk(entity_class=DengueMetaEntity, records=updated_records)
    logger.info("Finished")

            