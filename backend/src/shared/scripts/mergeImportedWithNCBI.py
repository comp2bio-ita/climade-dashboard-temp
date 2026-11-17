from models.database_models import DengueMetaEntity, GenbankSequenceDataEntity, ImportedMetadata
from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService
from shared.utils.handlers.RegexHandler import RegexHandler


def mergeImportedWithNCBI():
    settings = EnvSettings()

    regexHandler = RegexHandler()

    dashDatabaseService = DatabaseService(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        database=settings.DASH_DATABASE,
        user=settings.DASH_USER,
        password=settings.DASH_PASSWORD
    )

    importedDengueCases = dashDatabaseService.list_records(entity_class=ImportedMetadata)

    dengueNcbiSequences = dashDatabaseService.list_records(entity_class=GenbankSequenceDataEntity)

    dengueDashSequences = []
    
    for imported in importedDengueCases:
        ncbiSeq = [seq for seq in dengueNcbiSequences if seq["accession_id"] == imported["accession_id"]]

        if not ncbiSeq:
            continue

        ncbiSeq = ncbiSeq[0]

        dengueDashSequences.append(
            DengueMetaEntity(
                genome_name = ncbiSeq["virus_name"],
                species = ncbiSeq["virus_name"],
                collection_date = ncbiSeq["release_date"],
                country =  regexHandler.match_country(ncbiSeq["location"]) if ncbiSeq["location"] else "unknown",
                host = ncbiSeq["host_name"] if ncbiSeq["host_name"] else "unknown",
                length = ncbiSeq["length"],
                lineage = imported["lineage"],
                serotype = imported["serotype"],
                genotype = imported["genotype"],
                major_lineage = imported["major_lineage"],
                minor_lineage = imported["minor_lineage"],
                genbank_sequence_data_id = ncbiSeq["accession_id"]
            )
        )


    if dengueDashSequences:
        print("Inserting...")
        dashDatabaseService.insert_bulk(records=dengueDashSequences)

    print("Done!")