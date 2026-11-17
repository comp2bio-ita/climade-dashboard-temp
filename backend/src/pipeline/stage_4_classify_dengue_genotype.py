from dotenv import load_dotenv
from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService
from shared.scripts.dengueRecognizers import dengueGenotypeRecognizer
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

    dengueGenotypeRecognizer(
        database_service=databaseService
    )

if __name__=="__main__":
    main()