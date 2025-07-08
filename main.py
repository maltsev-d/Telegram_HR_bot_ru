import asyncio
import logging
from aiogram import Router
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart, Command
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

from keyboards import yes_no_keyboard, single_button_keyboard, decision_keyboard
from vacancies import get_vacancies
from analytics import init_analytics, update_user_fields
from states import Form
import texts

#Заглушка для Reender
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
#-------------------------------------------------

# Настройка логирования
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не найдена или пуста!")

# Роутер
router = Router()

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    await state.set_state(Form.choose_vacancy)
    date_now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Логируем начало работы с пользователем
    logger.warning(f"Новый пользователь: {message.from_user.full_name}, ID: {message.from_user.id}")

    await update_user_fields(
        message.from_user.id,
        status="Новый",
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        date=date_now
    )

    kb = single_button_keyboard("🔍  Активные вакансии", "show_vacancies")
    await message.answer(
        texts.START_MESSAGE.format(message.from_user.first_name),
        reply_markup=kb
    )


@router.callback_query(lambda c: c.data == "show_vacancies")
async def show_vacancies(callback: CallbackQuery):
    """Показать доступные вакансии"""
    vacancies = get_vacancies()
    if not vacancies:
        logger.warning(f"Вакансии для пользователя {callback.from_user.id} не найдены.")
        await callback.message.answer("Нет подходящих вакансий.")

    for v in vacancies:
        kb = single_button_keyboard("👉  Откликнуться", f"apply_{v['id']}")
        await callback.message.answer(f"*{v['title']}*\n\n{v['description']}", reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("apply_"))
async def apply(callback: CallbackQuery, state: FSMContext):
    """Откликнуться на вакансию"""
    vacancy_id = callback.data.split("_")[1]
    vacancies = get_vacancies()
    vacancy = next((v for v in vacancies if v["id"] == vacancy_id), None)

    if not vacancy:
        await callback.answer("Вакансия не найдена.")
        return

    await update_user_fields(callback.from_user.id,
                             vacancy=f"{vacancy['title']}",
                             status="Ознакомление"
                             )

    await callback.message.answer(texts.VACANCY_INFO)

    kb = yes_no_keyboard("continue_yes", "continue_no")
    await callback.message.answer(texts.INTEREST_MESSAGE, reply_markup=kb)
    await state.set_state(Form.interest)


@router.callback_query(lambda c: c.data == "continue_no")
async def no_continue(callback: CallbackQuery, state: FSMContext):
    """Пользователь не заинтересован"""
    await callback.message.answer(texts.REJECTION_ASK)
    await state.set_state(Form.rejection_reason)


@router.message(Form.rejection_reason)
async def save_reason(message: Message, state: FSMContext):
    """Сохранить причину отказа"""
    await update_user_fields(message.from_user.id,
                             reason=message.text,
                             status="Отказ кандидата"
                             )

    await message.answer(texts.REJECTION_THANKS)
    await state.clear()


@router.callback_query(lambda c: c.data == "continue_yes")
async def ask_main_thing(callback: CallbackQuery, state: FSMContext):
    """Пользователь продолжает общение, задаём вопросы"""
    await callback.message.answer(texts.QUESTION_1)
    await state.set_state(Form.question_1)


@router.message(Form.question_1)
async def get_main_thing(message: Message, state: FSMContext):
    """Получение ответа на первый вопрос"""
    await update_user_fields(message.from_user.id, important=message.text)
    await message.answer(texts.QUESTION_2)
    await state.set_state(Form.question_2)


@router.message(Form.question_2)
async def process_salary(message: Message, state: FSMContext):
    """Обработка зарплатных ожиданий"""
    salary = message.text.strip()
    # Валидация зарплатных ожиданий
    try:
        salary_clean = int(salary.replace(' ', '').replace(',', ''))
        #if salary_clean < 10000 or salary_clean > 500000:
        #    raise ValueError("Значение вне допустимого диапазона")
    except ValueError:
        await message.answer(texts.SALARY_ERROR)
        return


    await update_user_fields(message.from_user.id, salary_expectations=salary)
    await state.set_state(Form.interview_invite)
    await interview_invite(message, state)


months_ru = {
    "January": "января", "February": "февраля", "March": "марта", "April": "апреля", "May": "мая", "June": "июня",
    "July": "июля",
    "August": "августа", "September": "сентября", "October": "октября", "November": "ноября", "December": "декабря",
}


@router.message(Form.interview_invite)
async def interview_invite(message: Message, state: FSMContext):
    """Приглашение на интервью"""
    # Расчёт 48 рабочих часов
    interview_datetime = datetime.now()
    hours_added = 0
    while hours_added < 48:
        interview_datetime += timedelta(hours=1)
        if interview_datetime.weekday() < 5 and 9 <= interview_datetime.hour < 18:
            hours_added += 1

    interview_date_str = interview_datetime.strftime('%d')
    month_en = interview_datetime.strftime('%B')
    month_ru = months_ru.get(month_en, month_en)
    interview_time = interview_datetime.strftime('%H:%M')

    interview_datetime = interview_datetime.strftime("%d.%m.%Y %H:%M")
    await update_user_fields(message.from_user.id,
                             status="Приглашение",
                             interview_date=interview_datetime
                             )

    kb = yes_no_keyboard("interview_yes", "interview_no")

    await message.answer(
        texts.INTERVIEW_INVITE.format(
            message.from_user.first_name, interview_date_str, month_ru, interview_time),
        reply_markup=kb
    )
    await state.set_state(Form.interview_invite)


@router.callback_query(lambda c: c.data == "interview_yes")
async def interview_yes(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение интервью"""
    await update_user_fields(callback.from_user.id, status="Интервью HR")
    await callback.message.answer(texts.INTERVIEW_ACCEPT)
    await state.clear()


@router.callback_query(lambda c: c.data == "interview_no")
async def interview_no(callback: types.CallbackQuery, state: FSMContext):
    """Отказ от интервью"""
    kb = single_button_keyboard("Никогда", "never")
    await callback.message.answer(texts.INTERVIEW_REJECT, reply_markup=kb)
    await state.set_state(Form.reschedule)


@router.message(Form.reschedule)
async def process_reschedule(message: Message, state: FSMContext):
    """Обработка повторного интервью"""
    await update_user_fields(message.from_user.id,
                             status="Cвязаться",
                             desired_interview_time=message.text
                             )

    await message.answer(texts.RESCHEDULE_THANKS)
    await state.clear()


@router.callback_query(lambda c: c.data == "never")
async def never_reason(callback: types.CallbackQuery, state: FSMContext):
    """Отказ от интервью навсегда"""
    await callback.message.answer(texts.NEVER_REASON)
    await state.set_state(Form.refusal_reason)


@router.message(Form.refusal_reason)
async def process_refusal_reason(message: Message, state: FSMContext):
    """Процесс отказа от интервью"""
    await update_user_fields(message.from_user.id,
                             status="Отказ кандидата",
                             refusal_reason=message.text
                             )

    await message.answer(texts.REFUSAL_THANKS)
    await state.clear()


@router.message(lambda m: m.text.startswith("/evaluate"))
async def evaluate_candidate(message: Message):
    """Оценка кандидата"""
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(texts.EVALUATE_ERROR, parse_mode=None)
        return

    user_id = int(parts[1])
    kb = decision_keyboard(user_id)
    await message.answer(f"🔍 Пора принять решение по кандидату с ID {user_id}. Выберите одно из действий ниже:",
                         reply_markup=kb)


@router.callback_query(F.data.startswith("decision_accept_"))
async def accept_candidate(callback: CallbackQuery):
    """Принять кандидата"""
    user_id = callback.data.split("_")[2]
    await update_user_fields(user_id, status="Принят")
    await bot.send_message(
        chat_id=user_id,
        text=texts.ACCEPT_CANDIDATE
    )
    await callback.message.answer(f"✅ Кандидат {user_id} получил уведомление о приеме.")
    await callback.answer()



@router.callback_query(F.data.startswith("decision_reject_"))
async def reject_candidate(callback: CallbackQuery, state: FSMContext):
    user_id = callback.data.split("_")[2]
    await state.set_state(Form.rejection_reason_final)
    await state.update_data(user_id=user_id)
    await callback.message.answer("Введите причину окончательного отказа кандидату:")
    await callback.answer()

@router.message(Form.rejection_reason_final)
async def save_final_rejection(message: Message, state: FSMContext):
    """Сохранить окончательный отказ"""
    data = await state.get_data()
    user_id = data.get("user_id")
    reason = message.text.strip()

    await update_user_fields(
        user_id,
        status="Непринят",
        final_rejection_reason=reason
    )

    await bot.send_message(
        chat_id=user_id,
        text=texts.REJECTION_FINAL
    )

    await message.answer(f"❌ Кандидату {user_id} отправлено уведомление об отказе.")
    await state.clear()

"""Выгрузка файла аналитики"""
@router.message(Command("download"))
async def send_csv(message: types.Message):
    file_path = "data/analytics.csv"
    try:
        document = FSInputFile(file_path, filename="analytics.csv")
        await message.answer_document(document, caption="Вот ваш файл аналитики 📊")
    except FileNotFoundError:
        await message.answer("Файл аналитики не найден 😕")

@router.message(Command("vacancies"))
async def show_vacancies_command(message: Message):
    """Команда для HR: показать все вакансии"""
    vacancies = get_vacancies()
    if not vacancies:
        await message.answer("Нет активных вакансий.")
        return

    for v in vacancies:
        await message.answer(f"*{v['title']}*\n\n{v['description']}")


"""Основная функция запуска бота"""
async def main():
    init_analytics()
    await dp.start_polling(bot)

# --- Заглушка для Render, чтобы он видел порт ---
def run_http():
    import os
    from http.server import HTTPServer, BaseHTTPRequestHandler

    port = int(os.environ.get("PORT", 8000))  # Render подставляет PORT
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"HR Bot is alive 🚀")

    httpd = HTTPServer(('0.0.0.0', port), Handler)
    httpd.serve_forever()

import threading
threading.Thread(target=run_http, daemon=True).start()
# --------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())

