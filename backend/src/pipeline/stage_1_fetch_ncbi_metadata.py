from dotenv import load_dotenv
from shared.utils.functions import convert_datetime_to_str_time, convert_str_time_to_datetime, datetime_add
from models.ncbi_models import VirusFilter
from shared.conf.taxonomy_ids import CHIK_TAX_ID, DENGUE_1_TAX, DENGUE_2_TAX, DENGUE_3_TAX, DENGUE_4_TAX, YFV_TAX_ID, ZIKA_TAX_ID
from models.database_models import GenbankSequenceDataEntity, UpdateLogs
from services.NcbiService import NcbiService
from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService

import logging

def main():

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    load_dotenv()

    settings = EnvSettings()

    databaseService  = DatabaseService(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        database=settings.DASH_DATABASE,
        user=settings.DASH_USER,
        password=settings.DASH_PASSWORD
    )

    dengue_filters = [
        GenbankSequenceDataEntity.virus_tax==DENGUE_1_TAX,
        GenbankSequenceDataEntity.virus_tax==DENGUE_2_TAX,
        GenbankSequenceDataEntity.virus_tax==DENGUE_3_TAX,
        GenbankSequenceDataEntity.virus_tax==DENGUE_4_TAX
    ]

    last_inserted_dengue_date = None
    last_inserted_zika_date = None
    last_inserted_chik_date = None
    last_inserted_yfv_date = None

    logging.info("Setting last updated date log")

    new_update_log = UpdateLogs(
        status="INITIALIZED",
        message="Initializing fetching NCBI data and preparing dashboard data"
    )
    
    databaseService.add_record(record=new_update_log)

    logging.info("Veryfying last inserted dengue, chik and zika metadata")

    # listing dengue
    query_results = list(databaseService.get_record_by_filters(entity_class=GenbankSequenceDataEntity, or_filters=dengue_filters, order_column="release_date", all_records=False))
    if query_results:
        last_inserted_dengue_metadata = GenbankSequenceDataEntity(**query_results[0])
        last_inserted_dengue_date = convert_str_time_to_datetime(last_inserted_dengue_metadata.release_date)

    # listing zika
    query_results = list(databaseService.get_record_by_filters(entity_class=GenbankSequenceDataEntity, and_filters=[GenbankSequenceDataEntity.virus_tax==ZIKA_TAX_ID], order_column="release_date", all_records=False))
    if query_results:
        last_inserted_zika_metadata = GenbankSequenceDataEntity(**query_results[0])
        last_inserted_zika_date = convert_str_time_to_datetime(last_inserted_zika_metadata.release_date)

    # listing chik
    query_results = list(databaseService.get_record_by_filters(entity_class=GenbankSequenceDataEntity, and_filters=[GenbankSequenceDataEntity.virus_tax==CHIK_TAX_ID], order_column="release_date", all_records=False))
    if query_results:
        last_inserted_chik_metadata = GenbankSequenceDataEntity(**query_results[0])
        last_inserted_chik_date = convert_str_time_to_datetime(last_inserted_chik_metadata.release_date)

    query_results = list(databaseService.get_record_by_filters(entity_class=GenbankSequenceDataEntity, and_filters=[GenbankSequenceDataEntity.virus_tax==YFV_TAX_ID], order_column="release_date", all_records=False))
    if query_results:
        last_inserted_yfv_metadata = GenbankSequenceDataEntity(**query_results[0])
        last_inserted_yfv_date = convert_str_time_to_datetime(last_inserted_yfv_metadata.release_date)


    logging.info("Converting date formats")


    last_inserted_dengue_date = convert_datetime_to_str_time(
        datetime_add(last_inserted_dengue_date, days=1)
    ) 
    last_inserted_zika_date =  convert_datetime_to_str_time(
        datetime_add(last_inserted_zika_date, days=1)
    ) 
    last_inserted_chik_date =  convert_datetime_to_str_time(
        datetime_add(last_inserted_chik_date, days=1)
    )
    last_inserted_yfv_date =  convert_datetime_to_str_time(
        datetime_add(last_inserted_yfv_date, days=1)
    )

    ncbiService = NcbiService()

    logging.info("Fetching missing NCBI zika metadata")

    ncbiSequencesMetadata = ncbiService.fetch_zika_metadata(
        filters=VirusFilter(released_since=last_inserted_zika_date) if last_inserted_zika_date else None
    )

    logging.info("Inserting missing NCBI zika metadata into the database")

    if ncbiSequencesMetadata:
        ncbiService.load_virus_metadata_to_db(ncbiSequencesMetadata)

    logging.info("Fetching missing NCBI Chikungunya metadata")

    ncbiSequencesMetadata = ncbiService.fetch_chick_metadata(
        filters=VirusFilter(released_since=last_inserted_chik_date) if last_inserted_chik_date else None
    )

    logging.info("Inserting missing NCBI chikungunya metadata into the database")

    if ncbiSequencesMetadata:
        ncbiService.load_virus_metadata_to_db(ncbiSequencesMetadata)

    logging.info("Fetching missing NCBI dengue metadata")

    ncbiSequencesMetadata = ncbiService.fetch_dengue_metadata(
        filters=VirusFilter(released_since=last_inserted_dengue_date) if last_inserted_dengue_date else None
    )

    logging.info("Inserting missing NCBI dengue metadata into the database")

    if ncbiSequencesMetadata:
        ncbiService.load_virus_metadata_to_db(ncbiSequencesMetadata)

    logging.info("Fetching missing NCBI yellow fever metadata")

    ncbiSequencesMetadata = ncbiService.fetch_yfv_metadata(
        filters=VirusFilter(released_since=last_inserted_yfv_date) if last_inserted_yfv_date else None
    )

    logging.info("Inserting missing NCBI yellow fever metadata into the database")

    if ncbiSequencesMetadata:
        ncbiService.load_virus_metadata_to_db(ncbiSequencesMetadata)

    logging.info("Finished..")
    

if __name__=="__main__":
    main()