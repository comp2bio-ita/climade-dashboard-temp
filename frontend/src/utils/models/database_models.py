from typing import TypeVar
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class GenbankSequenceDataEntity(Base):
    __tablename__ = "ncbi_sequence_data"

    accession_id = Column(String(50), primary_key=True)
    is_complete = Column(Boolean, nullable=True)
    is_annotated = Column(Boolean, nullable=True)
    isolate_name = Column(String(250), nullable=True)
    isolate_source = Column(String(100), nullable=True)
    isolate_collection_date = Column(String(250), nullable=True)
    source_database = Column(String(100), nullable=True)
    host_tax = Column(Integer, nullable=True)
    host_sci_name = Column(String(100), nullable=True)
    host_name = Column(String(100), nullable=True)
    virus_tax = Column(Integer, nullable=True)
    virus_sci_name = Column(String(100), nullable=True)
    virus_name = Column(String(100), nullable=True)
    virus_lineage = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    length = Column(Integer, nullable=True)
    gene_count = Column(Integer, nullable=True)
    submitter_affiliation = Column(String(1000), nullable=True)
    submitter_country = Column(String(100), nullable=True)
    update_date = Column(String(250), nullable=True)
    release_date = Column(String(250), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    
    # relationships
    chikungunya_meta = relationship("ChikungunyaMetaEntity", uselist=False, back_populates="genbank_sequence_data")
    dengue_meta = relationship("DengueMetaEntity", uselist=False, back_populates="genbank_sequence_data")
    zika_meta = relationship("ZikaMetaEntity", uselist=False, back_populates="genbank_sequence_data")
    yellow_fever_meta = relationship("YellowFeverMetaEntity", uselist=False, back_populates="genbank_sequence_data")


class ChikungunyaMetaEntity(Base):
    __tablename__ = 'chikungunya_meta_tb'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    genome_name = Column(String(100))
    species = Column(String(100))
    collection_date = Column(String(25))
    country = Column(String(100))
    host = Column(String(100))
    length = Column(Integer)
    lineage = Column(String(50))
    genotype = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

    # relationships
    genbank_sequence_data_id = Column(String(50), ForeignKey('ncbi_sequence_data.accession_id'))
    genbank_sequence_data = relationship("GenbankSequenceDataEntity", back_populates="chikungunya_meta")



class DengueMetaEntity(Base):
    __tablename__ = 'dengue_meta_tb'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    genome_name = Column(String(100))
    species = Column(String(100))
    collection_date = Column(String(25))
    country = Column(String(100))
    host = Column(String(100))
    length = Column(Integer)
    lineage = Column(String(20))
    serotype = Column(String(10))
    genotype = Column(String(10))
    major_lineage = Column(String(10))
    minor_lineage = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())

    # relationships
    genbank_sequence_data_id = Column(String(50), ForeignKey('ncbi_sequence_data.accession_id'))
    genbank_sequence_data = relationship("GenbankSequenceDataEntity", back_populates="dengue_meta")
    

class ZikaMetaEntity(Base):
    __tablename__ = 'zika_meta_tb'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    genome_name = Column(String(100))
    species = Column(String(100))
    collection_date = Column(String(25))
    country = Column(String(100))
    host = Column(String(100))
    length = Column(Integer)
    lineage = Column(String(50))
    genotype = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

    # relationships
    genbank_sequence_data_id = Column(String(50), ForeignKey('ncbi_sequence_data.accession_id'))
    genbank_sequence_data = relationship("GenbankSequenceDataEntity", back_populates="zika_meta")


class YellowFeverMetaEntity(Base):
    __tablename__ = 'yellow_fever_meta_tb'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    genome_name = Column(String(100))
    species = Column(String(100))
    collection_date = Column(String(25))
    country = Column(String(100))
    host = Column(String(100))
    length = Column(Integer)
    lineage = Column(String(50))
    genotype = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

    genbank_sequence_data_id = Column(String(50), ForeignKey('ncbi_sequence_data.accession_id'))
    genbank_sequence_data = relationship("GenbankSequenceDataEntity", back_populates="yellow_fever_meta")


class PhyloEntity(Base):

    __tablename__ = 'phylo_tb'

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    pathogen = Column(String(20), nullable=False)
    newick = Column(MEDIUMTEXT, nullable=True)

    time_tree_nexus = Column(MEDIUMTEXT, nullable=True)
    sequence_count = Column(Integer, nullable=True)
    accession_ids = Column(JSON, nullable=True)
    filter_params = Column(String(1000), nullable=True)
    accession_set_hash = Column(String(64), index=True, nullable=True)
    inference_method = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, server_default="pending")

    warnings = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    run_metadata = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ImportedMetadata(Base):
    __tablename__ = 'imported_metadata_tb'

    # Columns
    id = Column(Integer, primary_key=True, autoincrement=True)
    genome_name = Column(String(100), nullable=True)
    species = Column(String(100), nullable=True)
    collection_date = Column(String(25), nullable=True)
    country = Column(String(100), nullable=True)
    host = Column(String(100), nullable=True)
    lenght = Column(Integer, nullable=True) 
    lineage = Column(String(20), nullable=True)
    serotype = Column(String(10), nullable=True)
    genotype = Column(String(10), nullable=True)
    major_lineage = Column(String(10), nullable=True)
    minor_lineage = Column(String(20), nullable=True)
    accession_id = Column(String(50), nullable=True)
    virus = Column(String(50), nullable=True)


class UpdateLogs(Base):
    __tablename__ = 'update_logs_tb'

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(50), nullable=False)
    message = Column(String(500), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)


# Define a type variable
Entity = TypeVar('Entity', 
    GenbankSequenceDataEntity, 
    ChikungunyaMetaEntity, 
    DengueMetaEntity,
    ZikaMetaEntity,
    YellowFeverMetaEntity
)