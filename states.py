from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    ...
    choose_vacancy = State()
    salary_expectation = State()
    interview_invite = State()
    interview_reschedule = State()
    interest = State()
    refusal_reason = State()
    rejection_reason = (State())
    waiting_interest = State()
    question_1 = State()
    question_2 = State()
    waiting_salary = State()
    reschedule = State()
    decision = State()
    rejection_reason_final = State()