import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

import emoji
from aiogram import Bot, Dispatcher, types
from aiogram.filters import BaseFilter, CommandStart, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from src.db import Chat, get_or_create, init_tables, update_info
from src.words import router as word_router
from utils.settings import (
    ALLOWED_CHAT_ID,
    PING_TIMEDELTA,
    TOKEN,
    WORDS,
    get_logger,
    setup_logging,
)

setup_logging()
logger = get_logger()
init_tables()

timings: dict[str, datetime] = defaultdict(datetime)

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(word_router)


def get_days(days: int) -> str:
    if days % 10 == 1:
        return "день"
    elif (2 <= days % 10 <= 4) and (10 > days % 100 or days % 100 > 20):
        return "дня"
    else:
        return "дней"


def get_hours(hours: int) -> str:
    if hours % 10 == 1:
        return "час"
    elif (2 <= hours % 10 <= 4) and (10 > hours % 100 or hours % 100 > 20):
        return "часа"
    else:
        return "часов"


def get_minutes(minutes: int) -> str:
    if minutes % 10 == 1:
        return "минута"
    elif (2 <= minutes % 10 <= 4) and (10 > minutes % 100 or minutes % 100 > 20):
        return "минуты"
    else:
        return "минут"


def get_seconds(seconds: int) -> str:
    if seconds % 10 == 1:
        return "секунда"
    elif (2 <= seconds % 10 <= 4) and (10 > seconds % 100 or seconds % 100 > 20):
        return "секунды"
    else:
        return "секунд"


def get_normilized_message(message: str) -> str:
    result = message.lower()
    for mark in ",.-?!:;":
        result = result.replace(mark, " ")
    result = result.replace("  ", " ").split(" ")
    return result


class OnlyJopokorsarFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.id in ALLOWED_CHAT_ID


class OneMinuteFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        chat_obj: Chat = get_or_create(message.chat.id)[0]

        delta = datetime.now() - chat_obj.datetime_stamp
        logger.info("Delta is %s for chat %d", str(delta), message.chat.id)
        is_one_minute = delta < PING_TIMEDELTA
        if is_one_minute:
            update_info(chat_obj.id, datetime.now())
            return False
        return not is_one_minute


class JopokorsarTextFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.text is None:
            return False
        splitted_words = get_normilized_message(message.text)
        for word in WORDS:
            if all(map(lambda w: w in splitted_words, word.split(" "))):
                return True
        return False


@dp.message(CommandStart())
async def start(message: types.Message):
    chat_obj = get_or_create(message.chat.id)
    if chat_obj[1]:
        logger.info("Start tracking: %s", chat_obj[0])
        await message.answer(
            f"{emoji.emojize(':bomb:')} Отслеживание жопокорсара началось."
        )


@dp.message(
    JopokorsarTextFilter(), OnlyJopokorsarFilter(), OneMinuteFilter(), StateFilter(None)
)
async def cmd_test1(message: types.Message):
    chat_obj = get_or_create(message.chat.id)[0]
    logger.info("Triggered jopokorsar, old: %s", chat_obj)
    delta: timedelta = datetime.now() - chat_obj.datetime_stamp

    seconds: int = delta.seconds % 60
    minutes: int = (delta.seconds // 60) % 60
    hours: int = ((delta.seconds // 60) // 60) % 24
    days: int = delta.days

    message_delta: list = [
        f"{days} {get_days(days)}" if days != 0 else None,
        f"{hours} {get_hours(hours)}" if hours != 0 else None,
        f"{minutes} {get_minutes(minutes)}" if minutes != 0 else None,
        f"{seconds} {get_seconds(seconds)}" if seconds != 0 else None,
    ]
    while None in message_delta:
        if len(message_delta) == 0:
            break
        message_delta.remove(None)

    if message_delta:
        await message.reply(
            f"{emoji.emojize(':bomb:')}Время без жопокорсара: {' '.join(message_delta)} {emoji.emojize(':collision:')}"
        )
    del delta, message_delta, seconds, minutes, hours, days
    update_info(chat_obj.id, datetime.now())


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logger.info("Start")
    asyncio.run(main())
