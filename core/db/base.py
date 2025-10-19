from sqlalchemy import URL, create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

# TODO put in environment variables
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username="",
    password="",
    host="",
    port=,
    database="ci-cd",
)

engine = create_engine(url=DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True))
Base = declarative_base()
