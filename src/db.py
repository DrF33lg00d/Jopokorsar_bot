from datetime import datetime

from sqlalchemy import DateTime, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from utils.settings import DB_PATH, get_logger, setup_logging


setup_logging()
logger = get_logger()


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chat"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    datetime_stamp: Mapped[datetime] = mapped_column(DateTime(), default=datetime.now())

    def __repr__(self) -> str:
        return f"Chat(id={self.id!r}, datetime={self.datetime_stamp!r})"


ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=True)
SESSION = Session(ENGINE)


def init_tables() -> None:
    Base.metadata.create_all(ENGINE)


def update_info(id: int, new_dt_obj: datetime) -> None:
    try:
        query = select(Chat).where(Chat.id == id)
        chat_obj = SESSION.scalar(query)
    except Exception as e:
        logger.error("%s - %s", e.__class__, e.__context__)
        return None
    chat_obj.datetime_stamp = new_dt_obj
    SESSION.commit()
    logger.info("Chat %d change datetime to %s", id, str(new_dt_obj))


def get_or_create(id: int, dt_obj: datetime = datetime.now()) -> tuple[Chat, bool]:
    with Session(ENGINE) as session:
        try:
            chat_obj = Chat(id=id, datetime_stamp=dt_obj)
            session.add(chat_obj)
            session.commit()
            logger.info("Created new record: %s", chat_obj)
            return chat_obj, True
        except Exception as e:
            session.rollback()
            logger.warning("%s - %s", e.__class__.__name__, e.__context__)

        query = select(Chat).where(Chat.id == id)
        chat_obj = session.scalar(query)
        return chat_obj, False
