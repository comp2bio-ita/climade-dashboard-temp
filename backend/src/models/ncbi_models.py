
from typing import List, Optional
from pydantic import BaseModel

#########################
# DTO SUBMODELS
#########################


class VirusIsolate(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None
    collection_date: Optional[str] = None


class Lineage(BaseModel):
    tax_id: Optional[int] = None
    name: Optional[str] = None


class VirusHost(BaseModel):
    tax_id: Optional[int] = None
    sci_name: Optional[str] = None
    organism_name: Optional[str] = None
    common_name: Optional[str] = None
    lineage: List[Lineage] = None
    strain: Optional[str] = None
    pangolin_classification: Optional[str] = None
      


class Virus(BaseModel):
    tax_id: Optional[int] = None
    sci_name: Optional[str] = None
    organism_name: Optional[str] = None
    common_name: Optional[str] = None
    lineage: Optional[List[Lineage]] = None
    strain: Optional[str] = None
    pangolin_classification: Optional[str] = None


class ReportLocation(BaseModel):
    geographic_location: Optional[str] = None
    geographic_region: Optional[str] = None
    usa_state: Optional[str] = None


class ReportNucleotide(BaseModel):
    seq_id: Optional[str] = None
    accession_version: Optional[str] = None
    title: Optional[str] = None
    sequence_hash: Optional[str] = None


class ReportSubmitter(BaseModel):
    names: Optional[List[str]] = None
    affiliation: Optional[str] = None
    country: Optional[str] = None


#########################
# DTO MODELS
#########################


class VirusFilter(BaseModel):
    accessions: Optional[List[str]] = None
    taxon: Optional[str] = None
    refseq_only: Optional[bool] = None
    annotated_only: Optional[bool] = None
    released_since: Optional[str] = None             # should be formatted as '2020-04-01T00:00:00.000Z'
    updated_since: Optional[str] = None              # should be formatted as '2020-04-01T00:00:00.000Z'
    host: Optional[str] = None 
    pangolin_classification: Optional[str] = None
    geo_location: Optional[str] = None
    usa_state: Optional[str] = None
    complete_only: Optional[bool] = None


class VirusReport(BaseModel):
    accession: Optional[str] = None
    is_complete: Optional[bool] = None
    is_annotated: Optional[bool] = None
    lab_host: Optional[str] = None
    is_lab_host: Optional[bool] = None
    is_vaccine_strain: Optional[bool] = None
    source_database: Optional[str] = None
    protein_count: Optional[int] = None
    update_date: Optional[str] = None
    release_date: Optional[str] = None
    nucleotide_completeness: Optional[str] = None
    completeness: Optional[str] = None
    length: Optional[int] = None
    gene_count: Optional[int] = None
    mature_peptide_count: Optional[int] = None
    biosample: Optional[str] = None
    mol_type: Optional[str] = None
    purpose_of_sampling: Optional[str] = None
    isolate: Optional[VirusIsolate] = None
    host: Optional[VirusHost] = None
    virus: Optional[Virus] = None
    bioprojects: List[str] = None
    location: Optional[ReportLocation] = None
    nucleotide: Optional[ReportNucleotide] = None
    sra_accessions: Optional[List[str]] = None
    submitter: Optional[ReportSubmitter] = None
   


#########################
# HTTP RESPONSES MODELS
#########################


class VirusMetadataResponse(BaseModel):
    reports: Optional[List[VirusReport]] = None
    total_count: Optional[int] = None
    next_page_token: Optional[str] = None

class VirusRequestPayload(BaseModel):
    filter: Optional[VirusFilter] = None
    page_size: Optional[int] = None
    page_token: Optional[str] = None


