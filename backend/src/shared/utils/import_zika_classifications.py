from dotenv import load_dotenv
from models.database_models import ZikaMetaEntity
from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService
import logging
from pathlib import Path
import csv

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

    # Reading dataframes
    zika_file_path = Path(__file__).parents[2] / "data" / "final_global_zikv.csv"

    with zika_file_path.open("r", newline="", encoding="utf-8") as f:
        zika_df = list(csv.DictReader(f))

    if not zika_df:
        raise ValueError("Zika dataframe not found")

    unclassified_db_zika_records = database_service.get_record_by_filters(
        entity_class=ZikaMetaEntity,
        and_filters=[ZikaMetaEntity.genotype.is_(None)]
    ) 

    logger.info(f"Unclassified zika records: {len(unclassified_db_zika_records)}")

    if unclassified_db_zika_records:
        to_update_records = []

        logger.info("Updating Zika records")

        for item in zika_df:
            for db_record in unclassified_db_zika_records:
                if item["genbank_accession"] in db_record["genbank_sequence_data_id"]: 
                    db_record["genotype"] = item["variant"]
                    to_update_records.append(db_record)
                    break

        if to_update_records:
            logger.info(f"Committing zika records: {len(to_update_records)}")
            database_service.update_bulk(entity_class=ZikaMetaEntity, records=to_update_records)

    logger.info(f"Finished!")
    
if __name__=="__main__":
    main()