from datetime import UTC, datetime

from sqlalchemy import DATETIME, DateTime, ForeignKey, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from utils.settings import DB_PATH, get_logger, setup_logging

setup_logging()
logger = get_logger()
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=True)
SESSION = Session(ENGINE)


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chat"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    datetime_stamp: Mapped[datetime] = mapped_column(DateTime(), default=datetime.now())
    words: Mapped[list["BanWord"]] = relationship(back_populates="chat")

    def __repr__(self) -> str:
        return f"Chat(id={self.id!r}, datetime={self.datetime_stamp!r})"

    def add_banword(self, word: str) -> bool:
        word_instance = BanWord(text=word.lower(), chat=self)
        try:
            SESSION.add(word_instance)
            SESSION.commit()
            logger.debug("Created new word: %s", word_instance)
            return True
        except IntegrityError:
            SESSION.rollback()
            logger.debug("Already exists in DB")
        except Exception as e:
            SESSION.rollback()
            logger.warning("%s - %s", e.__class__.__name__, e.__context__)
        return False


class BanWord(Base):
    __tablename__ = "ban_word"
    text: Mapped[str] = mapped_column(String(), primary_key=True, unique=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chat.id"),
        primary_key=True,
    )
    chat: Mapped["Chat"] = relationship(back_populates="words")
    usages: Mapped[list["BanWordUsage"]] = relationship(
        "BanWordUsage",
        primaryjoin="and_(BanWord.text==BanWordUsage.text, BanWord.chat_id==BanWordUsage.chat_id)",
    )

    def __repr__(self) -> str:
        return f"Word '{self.text}'"

    def delete(self) -> bool:
        try:
            SESSION.delete(self)
            SESSION.commit()
            logger.debug("Word '%s' has been deleted", self.text)
            return True
        except Exception as e:
            SESSION.rollback()
            logger.error("%s - %s", e.__class__, e.__context__)
        return False

    def add_usage(self) -> bool:
        usage = BanWordUsage(
            date_time=datetime.now(UTC),
            text=self.text,
            chat_id=self.chat_id,
        )
        try:
            SESSION.add(usage)
            SESSION.commit()
            logger.debug(
                "Word '%s' used with datetime '%s'",
                self.text,
                usage.date_time.isoformat(),
            )
            return True
        except Exception as e:
            SESSION.rollback()
            logger.error("%s - %s", e.__class__, e.__context__)
        return False


class BanWordUsage(Base):
    __tablename__ = "ban_word_usage"
    date_time: datetime = mapped_column(DATETIME(), primary_key=True, nullable=False)
    text: Mapped[str] = mapped_column(ForeignKey("ban_word.text"), primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("ban_word.chat_id"), primary_key=True
    )

    def __repr__(self) -> str:
        return (
            f"Word '{self.text}' used {self.date_time.strftime('%y-%m-%d, %H:%M:%S')}"
        )


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
    logger.debug("Chat %d change datetime to %s", id, str(new_dt_obj))


def get_or_create(id: int, dt_obj: datetime = datetime.now()) -> tuple[Chat, bool]:
    try:
        chat_obj = Chat(id=id, datetime_stamp=dt_obj)
        SESSION.add(chat_obj)
        SESSION.commit()
        logger.info("Created new record: %s", chat_obj)
        return chat_obj, True
    except IntegrityError:
        SESSION.rollback()
        logger.debug("Already exists in DB")
    except Exception as e:
        SESSION.rollback()
        logger.warning("%s - %s", e.__class__.__name__, e.__context__)
    chat_obj = SESSION.get(Chat, id)
    return chat_obj, False
