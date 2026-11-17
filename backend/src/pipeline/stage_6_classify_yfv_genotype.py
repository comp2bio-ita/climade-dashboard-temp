from dotenv import load_dotenv
from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService
from shared.scripts.yfvRecognizers import yfvGenotypeRecognizer
import logging

def main():

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

    yfvGenotypeRecognizer(
        database_service=databaseService
    )

if __name__=="__main__":
    main()
