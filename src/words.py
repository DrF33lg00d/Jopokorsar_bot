from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from src.db import Chat, get_or_create
from utils.settings import get_logger

logger = get_logger()
router = Router()


class BanWordOperation(StatesGroup):
    adding_banword = State()
    removing_banword = State()


@router.message(StateFilter(*BanWordOperation.__state_names__), Command("cancel"))
@router.message(
    StateFilter(*BanWordOperation.__state_names__), F.text.lower() == "отмена"
)
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Нечего отменять")
        logger.debug("Nothing to cancel")
    else:
        await state.clear()
        await message.answer("Понял, отмена")
        logger.debug("Cancel operation, set state 'None'")


@router.message(Command("add_banword"), StateFilter(None))
async def cmd_add_banword(message: Message, state: FSMContext):
    await message.answer("Какое слово добавляем?")
    await state.set_state(BanWordOperation.adding_banword)
    await state.set_data({"chat": get_or_create(message.chat.id)[0]})
    logger.debug("Going to adding banword, set state 'adding_banword'")


@router.message(BanWordOperation.adding_banword, F.text)
async def add_banword(message: Message, state: FSMContext):
    state_data = await state.get_data()
    chat: Chat = state_data["chat"]
    is_word_added = chat.add_banword(message.text)
    if is_word_added:
        await message.answer("Слово добавлено")
        logger.debug("Banword '%s' added, set state 'None'", message.text.lower())
    else:
        await message.answer("Ошибка при добавлении слова")
        logger.debug("Banword '%s' not added, set state 'None'", message.text.lower())
    await state.clear()
