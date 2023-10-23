import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

import emoji
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import BaseFilter, Command
from aiogram.types import Message

from utils.settings import (
    TOKEN, ALLOWED_CHAT_ID, PING_TIMEDELTA, WORDS, setup_logging, get_logger,
)


setup_logging()
logger = get_logger()

timings: dict[str, datetime] = defaultdict(datetime)

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())


def get_days(days: int) -> str:
    if days % 10 == 1:
        return 'день'
    elif (2 <= days % 10 <= 4) and (10 > days % 100 or days % 100 > 20):
        return 'дня'
    else:
        return 'дней'

def get_hours(hours: int) -> str:
    if hours % 10 == 1:
        return 'час'
    elif (2 <= hours % 10 <= 4) and (10 > hours % 100 or hours % 100 > 20):
        return 'часа'
    else:
        return 'часов'

def get_minutes(minutes: int) -> str:
    if minutes % 10 == 1:
        return 'минута'
    elif (2 <= minutes % 10 <= 4) and (10 > minutes % 100 or minutes % 100 > 20):
        return 'минуты'
    else:
        return 'минут'

def get_seconds(seconds: int) -> str:
    if seconds % 10 == 1:
        return 'секунда'
    elif (2 <= seconds % 10 <= 4) and (10 > seconds % 100 or seconds % 100 > 20):
        return 'секунды'
    else:
        return 'секунд'


class OnlyJopokorsarFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return (
            message.chat.type in {'group', 'private'}
            and message.chat.id in ALLOWED_CHAT_ID
        )


class OneMinuteFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        saved_timing: datetime = timings.get(message.chat.id, None)
        if saved_timing is None:
            timings[message.chat.id] = datetime.now() + timedelta(seconds=1)
            logger.info('Set current datetime for chat %d', message.chat.id)
            return True
        delta = datetime.now() - saved_timing
        logger.info('Delta is %s for chat %d', str(delta), message.chat.id)
        is_one_minute = delta < PING_TIMEDELTA
        if is_one_minute:
            timings[message.chat.id] = datetime.now()
            return False
        return not is_one_minute


class JopokorsarTextFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        message_text = message.text.lower()
        if message_text is None:
            return False
        for word in WORDS:
            if all(map(lambda w: w in message_text, word.split(' '))):
                return True
        return False



@dp.message(Command('start'))
async def start(message: types.Message):
    logger.info('Start tracking chat %d', message.chat.id)
    if timings.get(message.chat.id) is None:
        timings[message.chat.id] = datetime.now()
    await message.answer(f'{emoji.emojize(":bomb:")} Отслеживание жопокорсара началось.')


@dp.message(JopokorsarTextFilter(), OnlyJopokorsarFilter(), OneMinuteFilter())
async def cmd_test1(message: types.Message):
    logger.info('Triggered jopokorsar, old: %s', str(timings[message.chat.id]))
    delta: timedelta = datetime.now() - timings[message.chat.id]

    seconds: int = delta.seconds % 60
    minutes: int = (delta.seconds // 60) % 60
    hours: int = ((delta.seconds // 60) // 60) % 24
    days: int = delta.days

    message_delta: list = [
        f'{days} {get_days(days)}' if days != 0 else None,
        f'{hours} {get_hours(hours)}' if hours != 0 else None,
        f'{minutes} {get_minutes(minutes)}' if minutes != 0 else None,
        f'{seconds} {get_seconds(seconds)}' if seconds != 0 else None,
    ]
    while None in message_delta:
        if len(message_delta) == 0:
            break
        message_delta.remove(None)

    if message_delta:
        await message.reply(f'{emoji.emojize(":bomb:")}Время без жопокорсара: {" ".join(message_delta)} {emoji.emojize(":collision:")}')
    del delta, message_delta, seconds, minutes, hours, days
    timings[message.chat.id] = datetime.now()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    asyncio.run(main())
