from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from utils.settings import get_logger

logger = get_logger()
router = Router()


class BanWordOperation(StatesGroup):
    adding_banword = State()
    removing_banword = State()


@router.message(Command("add_banword"), StateFilter(None))
async def cmd_add_banword(message: Message, state: FSMContext):
    await message.answer("Какое слово добавляем?")
    await state.set_state(BanWordOperation.adding_banword)
    logger.debug("Going to adding banword, set state 'adding_banword'")


@router.message(StateFilter(BanWordOperation.__state_names__), Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await message.answer("Понял, отмена")
    await state.set_state()
    logger.debug("Cancel operation, set state 'None'")


@router.message(BanWordOperation.adding_banword, F.text)
async def add_banword(message: Message, state: FSMContext):
    await message.answer("Триггер-слово настроено")
    await state.set_state()
    logger.debug("Banword '%s' added, set state 'None'", message.text.lower())
