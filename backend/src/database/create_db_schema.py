from dotenv import load_dotenv
from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService
from models import database_models  # noqa: F401
import logging

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
        password=settings.DASH_PASSWORD #,
        # publikey_retrieval=True,
    )

    logger.info("Creating Database Schema ...")

    database_service.create_all_tables_dashboard()

    logger.info("Database Schema Created")


    
    
if __name__=="__main__":
    main()