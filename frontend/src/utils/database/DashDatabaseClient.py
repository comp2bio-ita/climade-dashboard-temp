from utils.models.EnvSettings import EnvSettings

from typing import List, Type
import sqlalchemy as sqla
from sqlalchemy.orm import sessionmaker

from utils.models.database_models import (
    UpdateLogs,
    PhyloEntity,
    GenbankSequenceDataEntity,
)

# from models.database_models import Entity


class DashDatabaseClient:

    def __init__(self):
        self.settings = EnvSettings()
        db_url = f"mysql+pymysql://{self.settings.DASH_USER}:{self.settings.DASH_PASSWORD}@{self.settings.DASH_HOST}:{self.settings.DASH_PORT}/{self.settings.DASH_DATABASE}"
        self.engine = sqla.create_engine(
            db_url, 
            pool_recycle=3600, 
            pool_pre_ping=True,
            pool_size=50, 
            connect_args={"connect_timeout": 3600},
            max_overflow=50
        )

    def __open_connection(self) -> sessionmaker:
        try:
            SessioMaker = sessionmaker(bind=self.engine)
            session = SessioMaker()
            session.autoflush = False
            return session
        except Exception as e:
            print(f"Error while opening MySQL session: {e}")

    def __close_connection(self, session: sessionmaker) -> None:
        try:
            if session:
                session.close()
        except Exception as e:
            print(f"Error while closing session: {e}")

    def __row2dict(self, row: any):
        return {column.name: getattr(row, column.name) for column in row.__table__.columns}

    def list_records(self, entity_class: Type) -> List[dict]:
        session = self.__open_connection()
        all_records =  session.query(entity_class).all()
        converted_results = [self.__row2dict(row) for row in all_records]
        self.__close_connection(session=session)
        return converted_results
    
    def get_locations_for_accessions(self, accession_ids):
        if not accession_ids:
            return {}
        session = self.__open_connection()
        rows = (
            session.query(
                GenbankSequenceDataEntity.accession_id,
                GenbankSequenceDataEntity.location,
            )
            .filter(GenbankSequenceDataEntity.accession_id.in_(accession_ids))
            .all()
        )
        self.__close_connection(session=session)
        return {accession: location for accession, location in rows}

    def get_last_update(self, entity_class: UpdateLogs) -> dict:
        session = self.__open_connection()

        all_records =  session.query(entity_class).order_by(entity_class.timestamp.desc()).limit(1).all()

        converted_results = [self.__row2dict(row) for row in all_records]

        self.__close_connection(session=session)

        return converted_results[0] if converted_results else None

    def add_phylo_job(self, filter_params_json, accession_ids, pathogen, inference_method=None):
        # Insert pending job for the backend watcher
        session = self.__open_connection()
        phylo_job = PhyloEntity(
            pathogen=pathogen,
            status="pending",
            filter_params=filter_params_json,
            accession_ids=accession_ids,
            inference_method=inference_method,
        )
        session.add(phylo_job)
        session.commit()
        new_job_id = phylo_job.id
        self.__close_connection(session=session)
        return new_job_id

    def get_phylo_job_status(self, job_id):
        # Poll without tree columns (payload size)
        session = self.__open_connection()
        row = (
            session.query(
                PhyloEntity.id,
                PhyloEntity.status,
                PhyloEntity.warnings,
                PhyloEntity.error_message,
                PhyloEntity.sequence_count,
                PhyloEntity.inference_method,
            )
            .filter(PhyloEntity.id == job_id)
            .first()
        )
        self.__close_connection(session=session)
        return dict(row._mapping) if row else None

    def get_phylo_job_result(self, job_id):
        # Full job once terminal (trees + metadata)
        session = self.__open_connection()
        rows = (
            session.query(PhyloEntity)
            .filter(PhyloEntity.id == job_id)
            .limit(1)
            .all()
        )
        job = self.__row2dict(rows[0]) if rows else None
        self.__close_connection(session=session)
        return job

    def get_tip_metadata(self, accession_ids, pathogen):
        """Tip epi fields joined after inference; not in Newick.

        The metadata table is resolved from the pathogen registry, so supporting another
        arbovirus is a registry entry rather than a change here. Fields the pathogen does
        not declare are simply absent from the rows.
        """
        from pathogens import get_pathogen

        if not accession_ids:
            return {}

        meta_entity = get_pathogen(pathogen)["meta_entity"]
        declared = get_pathogen(pathogen)["phylo_metadata_fields"]
        available = {column.name for column in meta_entity.__table__.columns}
        # collection_date is not a colour-by option but every hover row shows it
        meta_columns = [field for field in list(declared) + ["collection_date"]
                        if field in available]

        session = self.__open_connection()
        rows = (
            session.query(meta_entity, GenbankSequenceDataEntity)
            .outerjoin(
                GenbankSequenceDataEntity,
                meta_entity.genbank_sequence_data_id == GenbankSequenceDataEntity.accession_id,
            )
            .filter(meta_entity.genbank_sequence_data_id.in_(accession_ids))
            .all()
        )
        metadata_by_accession = {}
        for pathogen_meta, genbank_sequence in rows:
            accession = pathogen_meta.genbank_sequence_data_id
            fields = {column: getattr(pathogen_meta, column) for column in meta_columns}
            # region and location live on the GenBank row, not the pathogen table
            fields["location"] = genbank_sequence.location if genbank_sequence else None
            fields["region"] = genbank_sequence.region if genbank_sequence else None
            metadata_by_accession[accession] = fields
        self.__close_connection(session=session)
        return metadata_by_accession


