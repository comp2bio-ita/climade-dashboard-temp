import pipeline.stage_1_fetch_ncbi_metadata as stage1
import pipeline.stage_2_prepare_dashboard_data as stage2
import pipeline.stage_3_classify_dengue_serotype as stage3
import pipeline.stage_4_classify_dengue_genotype as stage4
import pipeline.stage_5_classify_chikv_genotype as stage5
import pipeline.stage_6_classify_yfv_genotype as stage6
import time

from dotenv import load_dotenv

from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService
from services.normalization.service import normalize_pending_locations


def _normalize_pending_locations() -> None:
    load_dotenv()
    settings = EnvSettings()
    database_service = DatabaseService(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        database=settings.DASH_DATABASE,
        user=settings.DASH_USER,
        password=settings.DASH_PASSWORD,
    )
    normalize_pending_locations(database_service)


def main():
    stage1.main()
    time.sleep(10)
    _normalize_pending_locations()
    time.sleep(10)
    stage2.main()
    time.sleep(10)
    stage3.main()
    time.sleep(10)
    stage4.main()
    time.sleep(10)
    stage5.main()
    time.sleep(10)
    stage6.main()
    time.sleep(10)

    
if __name__ == "__main__":
    main()