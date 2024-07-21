# Step 1: Install necessary libraries (do this in your terminal)
# pip install aiogram sqlalchemy aiosqlite

import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json

API_TOKEN = '6915473619:AAFtuM1-FDx7n7Uqnf2gb7d2tJMIrgcWFeo'
ADMIN_ID = 2017535015  # Replace with your admin ID

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///social_credits.db')
Session = sessionmaker(bind=engine)
session = Session()

# Load ranks from JSON
with open('ranks.json', 'r') as file:
    ranks = json.load(file)


# Define FSM states
class ChangeCredit(StatesGroup):
    waiting_for_user_selection = State()
    waiting_for_credit_amount = State()
    waiting_for_reason = State()


class AddUserToRoom(StatesGroup):
    waiting_for_room_code = State()


# Step 3: Define Database Models

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True)
    username = Column(String, unique=True)
    social_credits = Column(Integer, default=0)
    room_id = Column(Integer, ForeignKey('rooms.id'))
    room = relationship('Room')


class SocialCreditHistory(Base):
    __tablename__ = 'social_credit_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    credits_change = Column(Integer)
    reason = Column(String)
    user = relationship('User')


Base.metadata.create_all(engine)


# Step 4: Helper functions

def get_rank(credits):
    for rank in ranks:
        if rank['min_soc_credit'] <= credits <= rank['max_soc_credit']:
            return rank['name']
    return "Unranked"


def credits_needed_for_next_rank(credits):
    for rank in ranks:
        if credits < rank['min_soc_credit']:
            return rank['min_soc_credit'] - credits
    return 0


def create_profile_message(user):
    rank = get_rank(user.social_credits)
    next_rank_credits = credits_needed_for_next_rank(user.social_credits)
    return f"Rank: {rank}\nCredits: {user.social_credits}\nCredits needed for next rank: {next_rank_credits}"


def main_keyboard(is_admin=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Profile"), KeyboardButton("Global Ranking"))
    markup.add(KeyboardButton("History"))
    if is_admin:
        markup.add(KeyboardButton("Change Credits"), KeyboardButton("Add User to Room"))
    return markup


# Step 5: Handlers and commands

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    tg_id = message.from_user.id
    username = message.from_user.username
    user = session.query(User).filter_by(tg_id=tg_id).first()
    if not user:
        user = User(tg_id=tg_id, username=username, social_credits=0)
        session.add(user)
        session.commit()
        logger.info(f"New user created: {username} (ID: {tg_id})")
    is_admin = (tg_id == ADMIN_ID)
    await message.answer("Welcome! Use the buttons below to navigate.", reply_markup=main_keyboard(is_admin))
    logger.info(f"User {username} started the bot.")


@dp.message_handler(lambda message: message.text == "Profile")
async def profile_handler(message: types.Message):
    tg_id = message.from_user.id
    user = session.query(User).filter_by(tg_id=tg_id).first()
    if user:
        profile_message = create_profile_message(user)
        await message.answer(profile_message)
        logger.info(f"User {user.username} requested profile.")
    else:
        await message.answer("User not found.")
        logger.warning(f"Profile request failed: User with ID {tg_id} not found.")


@dp.message_handler(lambda message: message.text == "Global Ranking")
async def global_ranking_handler(message: types.Message):
    users = session.query(User).order_by(User.social_credits.desc()).all()
    ranking = "Global Ranking:\n"
    for user in users:
        ranking += f"{user.username}: {user.social_credits} credits\n"
    await message.answer(ranking)
    logger.info(f"User {message.from_user.username} requested global ranking.")


@dp.message_handler(lambda message: message.text == "History")
async def history_handler(message: types.Message):
    tg_id = message.from_user.id
    user = session.query(User).filter_by(tg_id=tg_id).first()
    if user:
        history = session.query(SocialCreditHistory).filter_by(user_id=user.id).all()
        history_message = "Credit History:\n"
        for record in history:
            history_message += f"{record.credits_change} credits: {record.reason}\n"
        await message.answer(history_message)
        logger.info(f"User {user.username} requested history.")
    else:
        await message.answer("User not found.")
        logger.warning(f"History request failed: User with ID {tg_id} not found.")


# Step 6: Admin functionalities

@dp.message_handler(lambda message: message.text == "Change Credits" and message.from_user.id == ADMIN_ID)
async def change_credits_handler(message: types.Message):
    users = session.query(User).all()
    user_buttons = [InlineKeyboardButton(user.username, callback_data=f'change_{user.id}') for user in users]
    markup = InlineKeyboardMarkup(row_width=1).add(*user_buttons)
    await message.answer("Select a user to change credits:", reply_markup=markup)
    await ChangeCredit.waiting_for_user_selection.set()
    logger.info(f"Admin {message.from_user.username} initiated credit change process.")


@dp.callback_query_handler(lambda c: c.data.startswith('change_'), state=ChangeCredit.waiting_for_user_selection)
async def process_change_credits_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split('_')[1])
    await state.update_data(user_id=user_id)
    await bot.send_message(callback_query.from_user.id, "Enter the amount of credits to change:")
    await ChangeCredit.waiting_for_credit_amount.set()
    logger.info(f"Admin {callback_query.from_user.username} selected user with ID {user_id} for credit change.")


@dp.message_handler(state=ChangeCredit.waiting_for_credit_amount)
async def change_credits_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        await state.update_data(amount=amount)
        await message.answer("Enter the reason for the credit change:")
        await ChangeCredit.waiting_for_reason.set()
        logger.info(f"Admin {message.from_user.username} entered amount {amount} for credit change.")
    except ValueError:
        await message.answer("Please enter a valid number.")
        logger.warning(f"Invalid credit amount entered by admin {message.from_user.username}: {message.text}")


@dp.message_handler(state=ChangeCredit.waiting_for_reason)
async def change_credits_reason(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data['user_id']
    amount = data['amount']
    reason = message.text

    user = session.query(User).get(user_id)
    if user:
        user.social_credits += amount
        session.add(SocialCreditHistory(user_id=user.id, credits_change=amount, reason=reason))
        session.commit()
        await message.answer("Credits updated successfully.")
        logger.info(
            f"Admin {message.from_user.username} changed credits for user {user.username} by {amount}. Reason: {reason}")
    else:
        await message.answer("User not found.")
        logger.warning(f"Credit change failed: User with ID {user_id} not found.")
    await state.finish()


@dp.message_handler(lambda message: message.text == "Add User to Room" and message.from_user.id == ADMIN_ID)
async def add_user_to_room_handler(message: types.Message):
    await message.answer("Enter the room code:")
    await AddUserToRoom.waiting_for_room_code.set()
    logger.info(f"Admin {message.from_user.username} initiated add user to room process.")


@dp.message_handler(state=AddUserToRoom.waiting_for_room_code)
async def room_code_handler(message: types.Message, state: FSMContext):
    room_code = message.text
    room = session.query(Room).filter_by(name=room_code).first()
    if room:
        tg_id = message.from_user.id
        user = session.query(User).filter_by(tg_id=tg_id).first()
        if user:
            user.room = room
            session.commit()
            await message.answer("You have been added to the room.")
            logger.info(f"User {user.username} added to room {room.name}.")
        else:
            await message.answer("User not found.")
            logger.warning(f"Add to room failed: User with ID {tg_id} not found.")
    else:
        await message.answer("Invalid room code.")
        logger.warning(f"Invalid room code entered by {message.from_user.username}: {room_code}")
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
