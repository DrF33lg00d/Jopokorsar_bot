from collections import defaultdict
from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db import BanWord, BanWordUsage, Chat, get_or_create
from utils.settings import WORDS_LIMIT, get_logger

logger = get_logger()
router = Router()


class BanWordOperation(StatesGroup):
    adding_banword = State()
    removing_banword = State()


class WordCallbackFactory(CallbackData, prefix="fabnum"):
    action: str
    value: str


def get_keyboard_words(words: list[BanWord]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="отмена",
        callback_data=WordCallbackFactory(action="cancel", value="cancel"),
    )
    for word in words:
        builder.button(
            text=word.text,
            callback_data=WordCallbackFactory(action="delete", value=word.text),
        )
    builder.adjust(1, 5, repeat=True)
    return builder.as_markup()


@router.message(StateFilter(*BanWordOperation.__state_names__), Command("cancel"))
@router.message(
    StateFilter(*BanWordOperation.__state_names__), F.text.lower() == "отмена"
)
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Нечего отменять")
        logger.debug("Nothing to cancel")
    else:
        await message.answer("Понял, отмена")
        logger.debug("Cancel operation, set state 'None'")
    await state.clear()


@router.message(Command("add_banword"), StateFilter(None))
async def cmd_add_banword(message: Message, state: FSMContext):
    chat_instance = get_or_create(message.chat.id)[0]
    if len(chat_instance.words) <= WORDS_LIMIT:
        await message.answer("Какое слово добавляем?")
        await state.set_state(BanWordOperation.adding_banword)
        await state.set_data({"chat": get_or_create(message.chat.id)[0]})
        logger.debug("Going to adding banword, set state 'adding_banword'")
    else:
        await message.answer("Превышен лимит слов в 100")


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


@router.message(Command("remove_banword"), StateFilter(None))
async def cmd_remove_banword(message: Message, state: FSMContext):
    chat_instance = get_or_create(message.chat.id)[0]
    if chat_instance.words:
        keyboard_markup = get_keyboard_words(chat_instance.words)
        await state.set_state(BanWordOperation.removing_banword)
        await state.set_data({"words": chat_instance.words})
        await message.answer("Доступные слова:", reply_markup=keyboard_markup)
        logger.debug(
            "Find %d words, set state 'removing_banword'", len(chat_instance.words)
        )
    else:
        await message.answer("Нет слов для удаления")
        await state.clear()
        logger.debug("No words to delete, set state 'None'")


@router.callback_query(
    BanWordOperation.removing_banword, WordCallbackFactory.filter(F.action == "delete")
)
async def remove_banword(
    callback: CallbackQuery, state: FSMContext, callback_data: WordCallbackFactory
):
    data = await state.get_data()
    words: list[BanWord] = data["words"]
    word_to_delete: BanWord = next(
        filter(lambda x: callback_data.value == x.text, words), None
    )
    is_deleted = word_to_delete.delete()
    if is_deleted:
        logger.debug("Word '%s' deleted, set state to 'None'", word_to_delete.text)
        await callback.message.edit_text(
            f"Слово '{word_to_delete.text}' удалено", reply_markup=None
        )
    else:
        await callback.message.edit_text(
            f"Слово '{word_to_delete.text}' не удалено", reply_markup=None
        )
    await state.clear()


@router.callback_query(
    StateFilter(*BanWordOperation.__state_names__),
    WordCallbackFactory.filter(F.action == "cancel"),
)
async def callback_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Удаление слова отменено")
    await state.clear()


@router.message(Command("statistics"), StateFilter(None))
async def cmd_statistics(message: Message):
    def get_statistics(usages: list[BanWordUsage]) -> dict[str, int]:
        month_ago = datetime.now(tz=UTC) - timedelta(weeks=4.5)
        filtered_usages = filter(
            lambda dt: dt.date_time.replace(tzinfo=UTC) >= month_ago, usages
        )
        results = defaultdict(int)
        for usage in filtered_usages:
            results[usage.text] += 1
        return dict(sorted(results.items(), key=lambda item: item[1], reverse=True))

    chat_instance = get_or_create(message.chat.id)[0]
    if chat_instance.words:
        results_usages = get_statistics(list(chat_instance.get_usages()))
        message_text = f"Добавленные в чате слова ({len(chat_instance.words)}):\n"
        message_text += ", ".join([f"'{word.text}'" for word in chat_instance.words])
        message_text += "\nСтатистика по использованию слов за последний месяц:\n"
        message_text += "\n".join(
            [f"'{word}' - {qty}" for word, qty in results_usages.items()]
        )
        await message.answer(message_text)
    else:
        await message.answer("Нет слов для сбора статистики")
