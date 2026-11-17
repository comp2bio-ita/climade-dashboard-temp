from typing import Dict, List, Type

import sqlalchemy as sqla
from sqlalchemy.orm import aliased, sessionmaker

from models.database_models import DashBase, Entity


class DatabaseService:

    def __init__(
        self,
        host: str,
        user: str,
        database: str,
        port: int,
        password: str,
        publikey_retrieval: bool = False,
        ssl_disabled: bool = True,
    ) -> None:

        db_url = (
            # f"mysql+mysqlconnector://{user}:{password}"
            f"mysql+pymysql://{user}:{password}"
            f"@{host}:{port}/{database}?ssl_disabled={str(ssl_disabled).lower()}"
        )

        # if publikey_retrieval:
            # db_url += "&allowPublicKeyRetrieval=true"
            # db_url += "&allow_public_key_retrieval=true"

        self.engine = sqla.create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
        )

    def _session(self):
        return self.Session()

    @staticmethod
    def _row_to_dict(row):
        return {
            column.name: getattr(row, column.name)
            for column in row.__table__.columns
        }

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def create_all_tables_dashboard(self):
        DashBase.metadata.create_all(self.engine)

    def delete_all_tables_dashboard(self):
        DashBase.metadata.drop_all(self.engine)

    # ------------------------------------------------------------------
    # Inserts
    # ------------------------------------------------------------------

    def add_record(self, record: Entity):

        session = self._session()

        try:
            session.add(record)
            session.commit()
            return record

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

    def add_records(self, records: List[Entity]):

        session = self._session()

        try:
            session.add_all(records)
            session.commit()
            return records

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

    def insert_bulk(self, records: List[Entity]):

        session = self._session()

        try:
            session.bulk_save_objects(records)
            session.commit()
            return records

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

    def update_bulk(self, entity_class: Type, records: List[dict]):

        session = self._session()

        try:
            session.bulk_update_mappings(entity_class, records)
            session.commit()
            return records

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_records(self, entity_class: Type):

        session = self._session()

        try:
            rows = session.query(entity_class).all()
            return [self._row_to_dict(r) for r in rows]

        finally:
            session.close()

    def get_record_by_filters(
        self,
        entity_class: Type,
        and_filters: List = None,
        or_filters: List = None,
        ilike_filters: Dict[str, str] = None,
        order_column: str = "created_at",
        order_desc: bool = True,
        all_records: bool = True,
    ):

        session = self._session()

        try:

            query = session.query(entity_class)

            if and_filters:
                query = query.filter(sqla.and_(*and_filters))

            if or_filters:
                query = query.filter(sqla.or_(*or_filters))

            if ilike_filters:
                for column_name, pattern in ilike_filters.items():

                    column = getattr(entity_class, column_name, None)

                    if column is None:
                        raise ValueError(
                            f"{entity_class.__name__} has no column '{column_name}'"
                        )

                    query = query.filter(column.ilike(f"%{pattern}%"))

            order_col = getattr(entity_class, order_column, None)

            if order_col is None:
                raise ValueError(
                    f"{entity_class.__name__} has no column '{order_column}'"
                )

            query = query.order_by(
                sqla.desc(order_col) if order_desc else sqla.asc(order_col)
            )

            if all_records:
                rows = query.all()
                return [self._row_to_dict(r) for r in rows]

            row = query.first()

            return [self._row_to_dict(row)] if row else []

        finally:
            session.close()

    def query_join(
        self,
        target_entity_class: Type,
        join_entity_class: Type,
    ):

        session = self._session()

        try:

            target_alias = aliased(target_entity_class)
            join_alias = aliased(join_entity_class)

            rows = (
                session.query(target_alias, join_alias)
                .join(join_alias)
                .all()
            )

            return rows

        finally:
            session.close()