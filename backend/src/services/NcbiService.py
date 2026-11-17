from typing import List
import time
import requests
from pathlib import Path

from models.database_models import GenbankSequenceDataEntity
from models.env_models import EnvSettings
from models.ncbi_models import VirusFilter, VirusMetadataResponse, VirusReport, VirusRequestPayload
from shared.conf.taxonomy_ids import ALL_DENGUE_TAX_IDS, CHIK_TAX_ID, YFV_TAX_ID, ZIKA_TAX_ID
from shared.utils.functions import chunk_array
import logging

class NcbiService:

    def __init__(self):
        self.ncbi_api_url = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha"
        self.logger = logging.getLogger(__name__)


    def __fetch_virus_metadata(self, payload: VirusRequestPayload = None) -> VirusMetadataResponse:

        payload = payload.model_dump(exclude_none=True, exclude_unset=True)

        response = requests.post(url=f"{self.ncbi_api_url}/virus", json=payload).json()

        if not response:
            return []

        return VirusMetadataResponse(**response)
    
    def __fetch_all_virus_metadata(self, filters: VirusFilter = None, start_page: str = None) -> List[VirusReport]:

        reports: List[VirusReport] = []

        next_page = True
        next_page_token = start_page if start_page else None

        self.logger.info("Feetching NCBI metadata")

        count = 0

        while next_page:
            try:
                self.logger.info(f"Next page: {next_page_token}")

                payload = VirusRequestPayload(filter=filters, page_token=next_page_token)

                response = self.__fetch_virus_metadata(payload)

                if not response or not response.reports:
                    next_page = False
                
                reports.extend(response.reports)
                
                if not response.next_page_token:
                    next_page = False

                next_page_token = response.next_page_token

                count = 0

                time.sleep(0.1)

            except Exception as e:
                date = time.asctime(time.localtime())
                log_message = f"Error fetching the ncbi virus metadata from page {next_page_token}\n"

                log_file = Path(__file__).parents[1] / "logs" / f"ncbi_fetch_{date}.log"

                with open(log_file, "w") as log:
                    log.write(log_message)

                self.logger.error(e)
                self.logger.error(count)
                count=count+1
                if count == 10:
                    raise(e)
                
                time.sleep(2)
                # Don't do nothing else other than printing the error, so the request will be made again

        return reports
    
    
    def fetch_dengue_metadata(self, start_page: str = None, dengue_taxon = str(ALL_DENGUE_TAX_IDS), filters: VirusFilter = None) -> List[VirusReport]:

        if not filters:
            filters = VirusFilter(taxon=dengue_taxon)
        else:
            filters.taxon = dengue_taxon

        dengue_metadata = self.__fetch_all_virus_metadata(filters=filters, start_page=start_page)

        return dengue_metadata
    

    def fetch_zika_metadata(self, start_page: str = None, zika_taxon = str(ZIKA_TAX_ID), filters: VirusFilter = None) -> List[VirusReport]:

        if not filters:
            filters = VirusFilter(taxon=zika_taxon)
        else:
            filters.taxon = zika_taxon

        zika_metadata = self.__fetch_all_virus_metadata(filters=filters, start_page=start_page)

        return zika_metadata
    
    
    def fetch_chick_metadata(self, start_page: str = None, chik_taxon = str(CHIK_TAX_ID), filters: VirusFilter = None) -> List[VirusReport]:

        if not filters:
            filters = VirusFilter(taxon=chik_taxon)
        else:
            filters.taxon = chik_taxon


        chik_metadata = self.__fetch_all_virus_metadata(filters=filters, start_page=start_page)

        return chik_metadata


    def fetch_yfv_metadata(self, start_page: str = None, yfv_taxon = str(YFV_TAX_ID), filters: VirusFilter = None) -> List[VirusReport]:

        if not filters:
            filters = VirusFilter(taxon=yfv_taxon)
        else:
            filters.taxon = yfv_taxon

        yfv_metadata = self.__fetch_all_virus_metadata(filters=filters, start_page=start_page)
        n_fetched = len(yfv_metadata)
        yfv_metadata = [
            report for report in yfv_metadata
            if "17d" not in (isolate := ((report.isolate.name or "").lower() if report.isolate else ""))
            and "vaccine" not in isolate
        ]
        n_excluded = n_fetched - len(yfv_metadata)
        if n_excluded:
            self.logger.info(
                "Excluded %s yellow fever vaccine-strain records from NCBI metadata",
                n_excluded,
            )

        return yfv_metadata


    def fetch_virus_metadata_by_accession(self, taxon: str, genbank_accession: List[str]) -> List[VirusReport]:

        filters = VirusFilter(taxon=taxon, accessions=genbank_accession)

        metadata = self.__fetch_all_virus_metadata(filters=filters)

        return metadata
    
    def load_virus_metadata_to_db(self, virus_metadata: List[VirusReport]) -> None:
        
        from services.DatabaseService import DatabaseService

        settings = EnvSettings()

        dashDatabaseService = DatabaseService(
            host=settings.DASH_HOST,
            port=settings.DASH_PORT,
            database=settings.DASH_DATABASE,
            user=settings.DASH_USER,
            password=settings.DASH_PASSWORD
        )        

        db_records = [
            GenbankSequenceDataEntity(
                accession_id=item.accession,
                is_complete=item.is_complete,
                is_annotated=item.is_annotated,
                isolate_name=item.isolate.name if item.isolate else None,
                isolate_source=item.isolate.source if item.isolate else None,
                isolate_collection_date=item.isolate.collection_date if item.isolate else None,
                source_database=item.source_database,
                host_tax=item.host.tax_id if item.host else None,
                host_sci_name=item.host.sci_name if item.host else None,
                host_name=item.host.organism_name if item.host else None,
                virus_tax=item.virus.tax_id if item.virus else None,
                virus_sci_name=item.virus.sci_name if item.virus else None,
                virus_name=item.virus.organism_name if item.virus else None,
                virus_lineage=item.virus.lineage[-1].name if item.virus else None,
                location=item.location.geographic_location if item.location else None,
                region=item.location.geographic_region if item.location else None,
                length=item.length,
                gene_count=item.gene_count,
                submitter_affiliation=item.submitter.affiliation if item.submitter else None,
                submitter_country=item.submitter.country if item.submitter else None,
                update_date=item.update_date,
                release_date=item.release_date
            ) for item in virus_metadata if item
        ]

        chunks = chunk_array(db_records, 50)

        self.logger.info("Loading NCBI sequences ...")

        for chunk in chunks:
            dashDatabaseService.insert_bulk(chunk)

        self.logger.info("Loading finished!")


    def export_metadata_reports_dataframe(self, path: str, filename: str, reports: List[VirusReport]) -> str:
        import csv

        dumped_reports = [
            item.model_dump(exclude_none=True, exclude_unset=True)
            for item in reports
        ]


        output_path = Path(path) / f"{filename}.csv"

        if not dumped_reports:
            output_path.write_text("")
            return str(output_path)

        fieldnames = sorted({
            key
            for report in dumped_reports
            for key in report.keys()
        })

        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                extrasaction="ignore"
            )

            writer.writeheader()
            writer.writerows(dumped_reports)

        return str(output_path)


