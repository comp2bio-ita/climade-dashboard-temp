
import logging

from dotenv import load_dotenv

from shared.utils.handlers.RegexHandler import RegexHandler
from models.database_models import ChikungunyaMetaEntity, DengueMetaEntity, GenbankSequenceDataEntity, UpdateLogs, YellowFeverMetaEntity, ZikaMetaEntity
from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService
from shared.conf.taxonomy_ids import CHIK_TAX_ID, DENGUE_1_TAX, DENGUE_2_TAX, DENGUE_3_TAX, DENGUE_4_TAX, YFV_TAX_ID, ZIKA_TAX_ID
from shared.utils.functions import convert_datetime_to_str_time, convert_str_time_to_datetime

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


    last_inserted_dengue_date = None
    last_inserted_zika_date = None
    last_inserted_chik_date = None
    last_inserted_yfv_date = None

    logging.info("Setting last updated date log")

    new_update_log = UpdateLogs(
        status="COMPLETED",
        message="Fetching NCBI data and preparing dashboard data"
    )

    databaseService.add_record(record=new_update_log)

    logging.info("Veryfying last inserted dengue sequence")

    # listing dengue
    query_results = list(databaseService.get_record_by_filters(entity_class=DengueMetaEntity, order_column="created_at", all_records=False))
    if query_results:
        last_inserted_dengue_metadata = DengueMetaEntity(**query_results[0])
        last_inserted_dengue_date = last_inserted_dengue_metadata.created_at

    logging.info("Veryfying last inserted zika sequence")

    # listing zika
    query_results = list(databaseService.get_record_by_filters(entity_class=ZikaMetaEntity, order_column="created_at", all_records=False))
    if query_results:
        last_inserted_zika_metadata = ZikaMetaEntity(**query_results[0])
        last_inserted_zika_date = last_inserted_zika_metadata.created_at

    logging.info("Veryfying last inserted chik sequence")

    # listing chik
    query_results = list(databaseService.get_record_by_filters(entity_class=ChikungunyaMetaEntity, order_column="created_at", all_records=False))
    if query_results:
        last_inserted_chik_metadata = ChikungunyaMetaEntity(**query_results[0])
        last_inserted_chik_date = last_inserted_chik_metadata.created_at

    logging.info("Veryfying last inserted yellow fever sequence")

    query_results = list(databaseService.get_record_by_filters(entity_class=YellowFeverMetaEntity, order_column="created_at", all_records=False))
    if query_results:
        last_inserted_yfv_metadata = YellowFeverMetaEntity(**query_results[0])
        last_inserted_yfv_date = last_inserted_yfv_metadata.created_at

    logging.info("Fetching missing ncbi dengue metadata")

    ncbi_dengue = list(databaseService.get_record_by_filters(
        entity_class=GenbankSequenceDataEntity,
        and_filters=[
            GenbankSequenceDataEntity.virus_tax.in_([DENGUE_1_TAX, DENGUE_2_TAX, DENGUE_3_TAX, DENGUE_4_TAX]), GenbankSequenceDataEntity.created_at>last_inserted_dengue_date
            ] if last_inserted_dengue_date else [GenbankSequenceDataEntity.virus_tax.in_([DENGUE_1_TAX, DENGUE_2_TAX, DENGUE_3_TAX, DENGUE_4_TAX])],
        order_column="created_at"
    ))

    logging.info("Fetching missing ncbi zika metadata")

    ncbi_zika = list(databaseService.get_record_by_filters(
        entity_class=GenbankSequenceDataEntity,
        and_filters=[
            GenbankSequenceDataEntity.virus_tax==ZIKA_TAX_ID, GenbankSequenceDataEntity.created_at>last_inserted_zika_date
        ] if last_inserted_zika_date else [GenbankSequenceDataEntity.virus_tax==ZIKA_TAX_ID],
        order_column="created_at"
    ))

    logging.info("Fetching missing ncbi chik metadata")

    ncbi_chik = list(databaseService.get_record_by_filters(
        entity_class=GenbankSequenceDataEntity,
        and_filters=[
            GenbankSequenceDataEntity.virus_tax==CHIK_TAX_ID, GenbankSequenceDataEntity.created_at>last_inserted_chik_date
        ] if last_inserted_chik_date else [GenbankSequenceDataEntity.virus_tax==CHIK_TAX_ID],
        order_column="created_at"
    ))

    logging.info("Fetching missing ncbi yellow fever metadata")

    ncbi_yfv = list(databaseService.get_record_by_filters(
        entity_class=GenbankSequenceDataEntity,
        and_filters=[
            GenbankSequenceDataEntity.virus_tax==YFV_TAX_ID, GenbankSequenceDataEntity.created_at>last_inserted_yfv_date
        ] if last_inserted_yfv_date else [GenbankSequenceDataEntity.virus_tax==YFV_TAX_ID],
        order_column="created_at"
    ))

    regexHandler = RegexHandler()


    if ncbi_dengue:
        logging.info("Creating new unclassified dengue records for the dashboard")
        new_dengue_records = [
            DengueMetaEntity(
                genome_name=ncbiSeq["virus_name"],
                species=ncbiSeq["virus_name"],
                collection_date=convert_datetime_to_str_time(
                    dt=convert_str_time_to_datetime(ncbiSeq["isolate_collection_date"]), 
                    dt_format="%Y-%m-%dT%H:%M:%SZ"
                ) if ncbiSeq["isolate_collection_date"] else ncbiSeq["release_date"],
                country=regexHandler.match_country(ncbiSeq["location"]) if ncbiSeq["location"] else "Unknown",
                host=ncbiSeq["host_name"] if ncbiSeq["host_name"] else "unknown",
                length=ncbiSeq["length"],
                lineage=ncbiSeq["virus_lineage"],
                serotype=None,
                genotype=None,
                major_lineage=None,
                minor_lineage=None,
                genbank_sequence_data_id = str(ncbiSeq["accession_id"])
            ) for ncbiSeq in ncbi_dengue
        ]

        databaseService.insert_bulk(new_dengue_records)
        

    if ncbi_zika:
        logging.info("Creating new unclassified zika records for the dashboard")
        new_zika_records = [
            ZikaMetaEntity(
                genome_name = ncbiSeq["virus_name"],
                species = ncbiSeq["virus_name"],
                collection_date=convert_datetime_to_str_time(
                    dt=convert_str_time_to_datetime(ncbiSeq["isolate_collection_date"]), 
                    dt_format="%Y-%m-%dT%H:%M:%SZ"
                ) if ncbiSeq["isolate_collection_date"] else ncbiSeq["release_date"],
                country =  regexHandler.match_country(ncbiSeq["location"]) if ncbiSeq["location"] else "Unknown",
                host = ncbiSeq["host_name"] if ncbiSeq["host_name"] else "unknown",
                length = ncbiSeq["length"],
                lineage = ncbiSeq["virus_lineage"],
                genotype = None,
                genbank_sequence_data_id = ncbiSeq["accession_id"]
            ) for ncbiSeq in ncbi_zika
        ]

        databaseService.insert_bulk(new_zika_records)
        

    if ncbi_chik:
        logging.info("Creating new unclassified chikungunya records for the dashboard")
        new_chik_records = [
            ChikungunyaMetaEntity(
                genome_name = ncbiSeq["virus_name"],
                species = ncbiSeq["virus_name"],
                collection_date=convert_datetime_to_str_time(
                    dt=convert_str_time_to_datetime(ncbiSeq["isolate_collection_date"]), 
                    dt_format="%Y-%m-%dT%H:%M:%SZ"
                ) if ncbiSeq["isolate_collection_date"] else ncbiSeq["release_date"],
                country =  regexHandler.match_country(ncbiSeq["location"]) if ncbiSeq["location"] else "unknown",
                host = ncbiSeq["host_name"] if ncbiSeq["host_name"] else "unknown",
                length = ncbiSeq["length"],
                lineage = ncbiSeq["virus_lineage"],
                genotype = None,
                genbank_sequence_data_id = ncbiSeq["accession_id"]
            ) for ncbiSeq in ncbi_chik
        ]

        databaseService.insert_bulk(new_chik_records)


    if ncbi_yfv:
        logging.info("Creating new unclassified yellow fever records for the dashboard")
        new_yfv_records = [
            YellowFeverMetaEntity(
                genome_name = ncbiSeq["virus_name"],
                species = ncbiSeq["virus_name"],
                collection_date=convert_datetime_to_str_time(
                    dt=convert_str_time_to_datetime(ncbiSeq["isolate_collection_date"]),
                    dt_format="%Y-%m-%dT%H:%M:%SZ"
                ) if ncbiSeq["isolate_collection_date"] else ncbiSeq["release_date"],
                country =  regexHandler.match_country(ncbiSeq["location"]) if ncbiSeq["location"] else "Unknown",
                host = ncbiSeq["host_name"] if ncbiSeq["host_name"] else "unknown",
                length = ncbiSeq["length"],
                lineage = ncbiSeq["virus_lineage"],
                genotype = None,
                genbank_sequence_data_id = ncbiSeq["accession_id"]
            ) for ncbiSeq in ncbi_yfv
        ]

        databaseService.insert_bulk(new_yfv_records)

    logging.info("Finishing pipeline!")

if __name__=="__main__":
    main()