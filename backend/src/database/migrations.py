import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models_production import Base

logger = logging.getLogger(__name__)


def get_database_url():
    return os.getenv("DATABASE_URL", "postgresql://wink_user:password@localhost:5432/wink_analytics")


def create_all_tables():
    database_url = get_database_url()
    engine = create_engine(database_url, echo=False)

    logger.info("Creating all tables from models_production...")
    Base.metadata.create_all(engine)
    logger.info("Tables created successfully")

    with engine.connect() as conn:
        logger.info("Creating additional indexes...")

        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_events_store_ts
                ON events(store_id, ts);
            """))
            conn.commit()
        except Exception as e:
            logger.warning(f"Index idx_events_store_ts may already exist: {e}")

        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_events_store_type_ts
                ON events(store_id, type, ts);
            """))
            conn.commit()
        except Exception as e:
            logger.warning(f"Index idx_events_store_type_ts may already exist: {e}")

        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_events_store_camera_person_ts
                ON events(store_id, camera_id, person_key, ts);
            """))
            conn.commit()
        except Exception as e:
            logger.warning(f"Index idx_events_store_camera_person_ts may already exist: {e}")

        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_events_payload_gin
                ON events USING gin(payload);
            """))
            conn.commit()
        except Exception as e:
            logger.warning(f"GIN index idx_events_payload_gin may already exist: {e}")

        logger.info("All indexes created successfully")

    engine.dispose()


def run():
    logger.info("Starting database migrations...")
    create_all_tables()
    logger.info("Database migrations completed successfully")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run()
