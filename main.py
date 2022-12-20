import logging
#import json
import os
import re
import asyncio
import aiogram.utils.markdown as md
import datetime
import random
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from aiogram.utils import exceptions, executor
from aiogram.utils.exceptions import (BotBlocked, MessageToEditNotFound, MessageCantBeEdited, MessageCantBeDeleted, MessageToDeleteNotFound)
from aiogram.utils.markdown import bold, code, italic, text
from contextlib import suppress
from config import (init_db, add_job, add_create_worker, select_worcker, select_task, select_task_full, count_task,
 count_users, delete_tick_worker, set_create_worker_user_id, sub_admin_addr,select_users_name_from_id,set_action_value_my_task,select_my_task, menu_data_cbu_update_ticket_users, sub_admin_select_ticket, select_users_ticket_addr, TOKEN)
from validate_email import validate_email



"""
Меню по правам:
    общее меню:
        (
            ('Созданые мной ticket', 'list_ticket'),                #Вывод созданных ticket's
            ('Добавить заявку', 'reg_ticket'),                      #Регистрация ticket
            ('О боте', 'bot_about'),                                #О боте
            ('Заявка на модератора/Исполнителя', 'create_worker'),  #Заявка на права модератора/Исполнителя
        )
        если sudo:
            (
                ('Инициализация базы', 'sudo_init_db'),             #Создание быза данных
                ('Броадкаст', 'sudo_broadcast'),                    #Рассылка сообщений заданным пользователям
                ('Bot_reload', 'bot_reload'),                       #Перезапуск скрипта бота
                ('Править sub-admins', 'sub_admin_set'),            #Править sub-admins
                ('Распределение ticket', 'ticket_select_worker'),   #Распределение ticket
            )
        если sub_admin:
            (
                ('Распределение ticket', 'ticket_select_worker'),   #Распределение ticket
            )
        в других случаях:
            (
                ('Help', 'help'),                                   #Помощь в работе
            )

Машина состояний (StatesGroup):
    Form:                       #регистрация ticket
        name_task                   #ticket кратко
        address_task                #Укажи подразделение (кнопкой)
        name_user                   #FIO заявителя
        phone_user                  #№ phone
        mail_user                   #mail
        text_task                   #full text ticket
        test_task_finish            #logistic-test & finish

    Form_broadcast:             #broadcast-message
        text_broadcast              #message-send

    Form_worker_query:          #регистрация модератора/Исполнителя
        worker_query_agree:         #принимаем согласие пользователя
        worker_query_role:          #спрашиваем роль
        worker_query_name:          #вводим FIO
        worker_query_addr:          #подразделение sub_admin's
        worker_query_confirm:       #подтверждение
    Form_task_id_key:
        task_id_key:

thistuple(списки/кортежи)
    addr:               #адреса подразделений
    sudo:               #список суперадминов
    sub_admin:               #список sub_admin
    broadcast:               #список broadcast получателей
    banned_users:               #список banned users

"""



# Объявление и инициализация объектов бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

keyboard_cb = CallbackData('post', 'id', 'action')  # post:<id>:<action>
#ОБРАБОТЧИКИ ФОРМ ДИАЛОГА
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# создаём форму создания заявки и указываем поля
class Form(StatesGroup):
    name_task = State()
    address_task = State()
    name_user = State()
    phone_user = State()
    mail_user = State()
    text_task = State()
    test_task_finish = State()
# создаём форму broadcast и указываем поля
class Form_broadcast(StatesGroup):
    text_broadcast = State()
# создаём форму moderador и указываем поля
class Form_worker_query(StatesGroup):
    worker_query_agree = State()
    worker_query_role = State()  
    worker_query_name = State()
    worker_query_addr = State()
    worker_query_confirm = State()
# отправка фото
class Form_task_id_key(StatesGroup):
    task_id_key = State()
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ОБРАБОТЧИКИ ФОРМ ДИАЛОГА

#СПИСКИ/КОРТЕЖИ/KEYBOARD
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
class kb():
    agree = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons_agree = ["Согласен", "Не согласен"]
    agree.add(*buttons_agree)

    role = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons_role = ["Распределение", "Выполнение"]
    role.add(*buttons_role)

    action_yes_no = types.InlineKeyboardMarkup(row_width=3)
    callback_action_yes = types.InlineKeyboardButton(text="Всё верно", callback_data='action_yes')
    callback_action_no = types.InlineKeyboardButton(text="Cancelled", callback_data='action_no')
    action_yes_no.add(callback_action_yes)
    action_yes_no.add(callback_action_no)

    action_delete = types.InlineKeyboardMarkup(row_width=1)
    callback_action_delete =types.InlineKeyboardButton(text='Удалить', callback_data='action_delete_tick_worker')
    action_delete.add(callback_action_delete)


class thistuple():
    #подразделения
    addr = ('АХЧ', 'Отдел охраны', 'Отдел технических систем безопасности', 'Службы главного инженера (ОГЭ и ОГМиТ)', 'УМЦ', 'Управление кадров', 'УИ')
    #суперадмины
    sudo = (312545008, 3125450081)
    #sub_admin
    sub_admin = (3125450081, 3125450081)
    #рассылка
    broadcast = (312545008, 312545008, 5153495001)
    #ban_list
    banned_users = (3125450081, 12312312)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! СПИСКИ/КОРТЕЖИ/KEYBOARD
version = 0.0827

async def on_startup():
    print(1231234564621353478235423654)
    print(1231234564621353478235423654)
    print(1231234564621353478235423654)
    print(1231234564621353478235423654)
    user_should_be_notified = 312545008  # Наверное это должны быть вы сами? Как всезнающий админ:)
    await bot.send_message(user_should_be_notified, 'Бот запущен')



#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#PRINT MENU BOT
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.message_handler(commands=['start'], commands_prefix='!/')
@dp.message_handler(commands=['menu'], commands_prefix='!/')
async def cmd_random_menu(message: types.Message):
    msg = await message.answer('Ожидайте ...')
    asyncio.create_task(delete_message(msg, 0.5))
    await asyncio.sleep(0.5)  # Timer
    keyboard_markup = types.InlineKeyboardMarkup(row_width=3)
    #GeneratorInlineKeyboardButton
    text_and_data_1_line = (
        ('Созданые мной ticket', 'list_ticket'),
        ('Добавить заявку', 'reg_ticket'),
        ('О боте', 'bot_about'),
        ('Заявка на модератора/Исполнителя', 'create_worker'),
    )
    if message.chat.id in thistuple.sudo:
        text_and_data_2_line = (
            ('Инициализация базы', 'sudo_init_db'),
            ('Броадкаст', 'sudo_broadcast'),
            ('Bot_reload', 'bot_reload'),
            ('Править sub-admins', 'sub_admin_set'),
            ('Распределение ticket', 'ticket_select_worker'),
        )
    #IF sub_admin
    elif message.chat.id in thistuple.sub_admin:
        text_and_data_2_line = (
            ('Добавить ticket', 'reg_ticket'),
            ('Распределение ticket', 'ticket_select_worker'),
        )
    else:
        text_and_data_2_line = (
            ('Добавить ticket', 'reg_ticket'),
        )

    # in real life for the menu_callback_data the callback action factory should be used
    # here the raw string is used for the simplicity
    row_btns = (types.InlineKeyboardButton(text, callback_data=action) for text, action in text_and_data_1_line)
    add_btns = (types.InlineKeyboardButton(text, callback_data=action) for text, action in text_and_data_2_line)
    keyboard_markup.row(*row_btns)
    keyboard_markup.add(*add_btns)
    await message.answer('Здравствуйте!\nВыберите действие.', reply_markup=keyboard_markup) 
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! PRINT MENU BOT
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


@dp.message_handler(commands='help', commands_prefix='!/')
async def cmd_block(message: types.Message, state: FSMContext):
    await asyncio.sleep(1.0)  # Здоровый сон на 10 секунд
    await message.answer('Федеральное государственное бюджетное образовательное учреждение высшего образования «Омский государственный технический университет', reply_markup=types.ReplyKeyboardRemove())

@dp.callback_query_handler(text='bot_about')  # if cb.data == 'bot_about'
async def inline_kb_answer_callback_handler(query: types.CallbackQuery):
    answer_data = query.data
    # always answer callback queries, even if you have nothing to say
    await query.answer(f'Вы выбрали: {answer_data!r}')

    if answer_data == 'bot_about':
        text = f'Справочно (потом заполнить)...\n v. {version}»'
    else:
        text = f'Unexpected callback data {answer_data!r}!'
    await query.answer(f'text')


#ФУНКЦИЯ БАНА
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.message_handler(user_id=thistuple.banned_users)
async def handle_banned(message: types.Message):
    print(f"{message.from_user.full_name} пишет, но мы ему не ответим!")
    return await message.reply("ID_Banned.")

@dp.message_handler(commands=['ban'], user_id=312545008) # здесь укажи свой ID
async def handle_ban_command1(message: types.Message):
    # проверяем, что ID передан правильно
    try:
        abuser_id = int(message.get_args())
    except (ValueError, TypeError):
        return await message.reply("Укажи ID пользователя.")

    thistuple.banned_users.append(abuser_id)
    await message.reply(f"Пользователь {abuser_id} заблокирован.")
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ФУНКЦИЯ БАНА


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ФУНКЦИЯ УДАЛЕНИЕ СООБЩЕНИЙ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
async def delete_message(message: types.Message, sleep_time: int = 0):
    await asyncio.sleep(sleep_time)
    with suppress(MessageCantBeDeleted, MessageToDeleteNotFound):
        await message.delete()
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ФУНКЦИЯ УДАЛЕНИЕ СООБЩЕНИЙ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ОТМЕНА ВСЕХ СТАДИЙ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
@dp.message_handler(commands='cancel', commands_prefix='!/')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return await bot.send_message(message.from_user.id, 'Отменять нечего.', reply_markup=types.ReplyKeyboardRemove())
    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ОТМЕНА ВСЕХ СТАДИЙ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ФУНКЦИЯ ВЫВОДА my_task
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.message_handler(commands=['my_task'], commands_prefix='!/')
async def cmd_random_my_task(message: types.Message):
    try:
        messages_my_task = select_my_task(user_id=message.from_user.id, limit=25)
        if len(messages_my_task) == 0:
            my_task_sql = "Нет данных."
        else:
            my_task_sql = '\n'.join([f'\n#/my_task{row[0]}\nКоротко:{row[1]}\nКому:{row[2]}\nСтатус:{row[3]}' for row in messages_my_task])
            count_task_user = count_task(user_id=message.from_user.id)
        await message.answer(f' Ваши ticket:\n {my_task_sql} \n\nВсего: \U0001D11A')
    except:
        print(f"ERROR ФУНКЦИЯ ВЫВОДА my_task")
    finally:
        logging.info(f"User {message.from_user.id} select task's.")
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ФУНКЦИЯ ВЫВОДА my_task
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ВЫВОД my_task В ПОЛНОМ ВВИДЕ (ЕГО ПРОВЕРКА И ФУНКЦИИ)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.message_handler(text_startswith=['my_task'])
async def text_startswith_handler_my_task(message: types.Message):
    await message.answer(f'Вы ввели запрос без /, вроверьте данные и повторите попытку (/{message.text})')
    await message.answer(f'\U0001F31A')

@dp.message_handler(text_startswith=['/my_task'])
async def text_startswith_handler_my_task(message: types.Message):
    try:
        messages_my_task_full = select_task_full(user_id=message.from_user.id, task_id_pk=message.text[8:])
        if messages_my_task_full is not None:
            # Configure InlineKeyboardMarkup
            keyboard_my_task_full = types.InlineKeyboardMarkup()
            keyboard_my_task_full.add(types.InlineKeyboardButton(text='Выполнено', callback_data='menu_value_my_task_1_'+str(messages_my_task_full[0])))
            keyboard_my_task_full.add(types.InlineKeyboardButton(text='Отклонено', callback_data='menu_value_my_task_2_'+str(messages_my_task_full[0])))
            await message.answer(
                    md.text(
                        md.text('<b>#ticket</b>', messages_my_task_full[0]),
                        md.text('Коротко:', messages_my_task_full[1]),
                        md.text('Кому:', messages_my_task_full[2]),
                        md.text('Ваши данные:', messages_my_task_full[3]),
                        md.text('Ваш телефон:', messages_my_task_full[4]),
                        md.text('Ваша почта:', messages_my_task_full[5]),
                        md.text('Тескт задачи:', messages_my_task_full[6]),
                        md.text('Исполнитель:', messages_my_task_full[7]),
                        md.text('Дата подачи:', messages_my_task_full[8]),
                        md.text('Закрытие:', messages_my_task_full[9]),
                        md.text('Статус:', messages_my_task_full[10]),
                        sep="\n"
                    ),
                reply_markup=keyboard_my_task_full,
                parse_mode=types.ParseMode.HTML,
                )
        else:
            await message.answer(f'Заявки №{message.text[8:]} от Вас не было, вроверьте данные и повторите попытку')
    except:
        print(f"ERROR ВЫВОД my_task В ПОЛНОМ ВВИДЕ")
    finally:
        logging.info(f"User {message.from_user.id} edit task {message.text[8:]}.")

# Обработчик кнопок действия над тикетом
@dp.callback_query_handler(text_contains='menu_value_my_task_')
async def menu_value_my_task(query: types.CallbackQuery):
    try:

        if query.data and query.data.startswith("menu_value_my_task_"):
            code = query.data[19]
            if code.isdigit():
                code = int(code)
            if code == 1:
                set_action_value_my_task(status_task="Выполнено", task_id_pk=query.data[21:])
                await query.message.edit_text('Нажата кнопка Выполнено')
            if code == 2:
                await query.message.edit_text('Нажата кнопка Отклонено')
                set_action_value_my_task(status_task="Отклонено", task_id_pk=query.data[21:])
            else:
                await bot.answer_callback_query(query.id)
    except:
        print(f"ERROR ВЫВОД my_task В ПОЛНОМ ВВИДЕ 222")
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ВЫВОД my_task В ПОЛНОМ ВВИДЕ (ЕГО ПРОВЕРКА И ФУНКЦИИ)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ВЫВОД ticket В ПОЛНОМ ВВИДЕ (ЕГО ПРОВЕРКА И ФУНКЦИИ)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.message_handler(text_startswith=['ticket'])
async def text_startswith_handler(message: types.Message):
    await message.answer(f'Вы ввели запрос без /, вроверьте данные и повторите попытку (/{message.text})')
    await message.answer(f'\U0001F31A')

@dp.message_handler(text_startswith=['/ticket'])
async def text_startswith_handler(message: types.Message):
    try:    
        messages_task_full = select_task_full(user_id=message.from_user.id, task_id_pk=message.text[7:])
        if messages_task_full is not None:
            # Configure InlineKeyboardMarkup
            keyboard_task_full = types.InlineKeyboardMarkup()
            keyboard_task_full.add(types.InlineKeyboardButton(text='Modify', callback_data='menu_value_ticket_1_'+str(messages_task_full[0])))
            keyboard_task_full.add(types.InlineKeyboardButton(text='Add Photo', callback_data='menu_value_ticket_2_'+str(messages_task_full[0])))
            keyboard_task_full.add(types.InlineKeyboardButton(text='Delete', callback_data='menu_value_ticket_3_'+str(messages_task_full[0])))
            await message.answer(
                    md.text(
                        md.text('<b>#ticket</b>', messages_task_full[0]),
                        md.text('Коротко:', messages_task_full[1]),
                        md.text('Кому:', messages_task_full[2]),
                        md.text('Ваши данные:', messages_task_full[3]),
                        md.text('Ваш телефон:', messages_task_full[4]),
                        md.text('Ваша почта:', messages_task_full[5]),
                        md.text('Тескт задачи:', messages_task_full[6]),
                        md.text('Исполнитель:', messages_task_full[7]),
                        md.text('Дата подачи:', messages_task_full[8]),
                        md.text('Закрытие:', messages_task_full[9]),
                        md.text('Статус:', messages_task_full[10]),
                        sep="\n"
                    ),
                reply_markup=keyboard_task_full,
                parse_mode=types.ParseMode.HTML,
                )
        else:
            await message.answer(f'Заявки №{message.text[7:]} от Вас не было, вроверьте данные и повторите попытку')
    except:
        print(f"ВЫВОД ticket В ПОЛНОМ ВВИДЕ")
    finally:
        logging.info(f"User {message.from_user.id} edit full_task {message.text[7:]}.")

# Обработчик кнопок действия над тикетом
@dp.callback_query_handler(text_contains='menu_value_ticket_')
async def menu(call: types.CallbackQuery, state: FSMContext):
    if call.data and call.data.startswith("menu_value_ticket_"):
        code = call.data[18]
        if code.isdigit():
            code = int(code)
        if code == 1:
            await call.message.edit_text('Нажата кнопка Modify')
        if code == 2:
            await Form_task_id_key.task_id_key.set()
            async with state.proxy() as data:
                data['task_id_key'] = call.data[20:]
            await call.message.edit_text(f'Ждём Photo к ticket  {call.data[20:]}')
        if code == 3:
            await call.message.edit_text('Нажата кнопка Delete')
        else:
            await bot.answer_callback_query(call.id)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ВЫВОД ticket В ПОЛНОМ ВВИДЕ (ЕГО ПРОВЕРКА И ФУНКЦИИ)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! Обработка фотографии
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.message_handler(content_types=['photo'], state=Form_task_id_key.task_id_key)
async def process_task_id_key(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        await bot.send_message(message.from_user.id, f"работает {data['task_id_key']}")
        #await message.photo[-1].download('test.jpg')
        #await bot.send_photo(312545008, f'{message.photo[-1]}')
        #photo11 = InputFile("test.jpg")
        #await bot.send_photo(chat_id=message.chat.id, photo=message.photo[-1])
        photo = open('test.jpg', 'rb')
        await bot.forward_message(312545008, message.from_user.id, message.message_id)    
    await state.finish()


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! Обработка фотографии
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ (СОЗДАНИЕ/УДАЛЕНИЕ) IF SUDO
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.callback_query_handler(text=['sudo_init_db'], user_id=thistuple.sudo)
async def handler_init_db(query: types.CallbackQuery):
    await query.answer(f'Создаю базу')
    init_db()
    await asyncio.sleep(2.0) #Timer
    await bot.send_message(query.from_user.id, f'SQLite3-created')
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ (СОЗДАНИЕ/УДАЛЕНИЕ) IF SUDO
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#Bot_reload IF SUDO
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.callback_query_handler(text=['bot_reload'], user_id=thistuple.sudo)
async def handler_bot_reload(query: types.CallbackQuery):
    await query.answer(f'bot_reload')
    await bot.send_message(query.from_user.id, f'bot_reload')
    await asyncio.sleep(1.1) #Timer
    os.system("sh restart.sh")
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! Bot_reload IF SUDO
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ФУНКЦИЯ БРОАДКАСТА IF SUDO
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def get_users():
    yield from (thistuple.broadcast)

async def send_message(user_id: int, text: str, disable_notification: bool = False) -> bool:
    try:
        await bot.send_message(user_id, text, disable_notification=disable_notification)
    except exceptions.BotBlocked:
        logging.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        logging.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        logging.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await send_message(user_id, text)  # Recursive call
    except exceptions.UserDeactivated:
        logging.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.TelegramAPIError:
        logging.exception(f"Target [ID:{user_id}]: failed")
    else:
        logging.info(f"Target [ID:{user_id}]: success")
        return True
    return False

@dp.callback_query_handler(text=['sudo_broadcast'], user_id=thistuple.sudo)
async def handler_broadcast(query: types.CallbackQuery):
    await Form_broadcast.text_broadcast.set()
    await query.answer(f'Ввод сообщения broadcast')
    await bot.send_message(query.from_user.id, f'Введите сообщение пользователям или /cancel для отмены.')

@dp.message_handler(state=Form_broadcast.text_broadcast)
async def handler_text_broadcast(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text_broadcast'] = message.text
        count = 0
        try:
            for user_id in get_users():
                if await send_message(user_id, data['text_broadcast']):
                    count += 1
                await asyncio.sleep(.05)  # 20 messages per second (Limit: 30 messages per second)
        finally:
            logging.info(f"{count} messages successful sent.")
            await bot.send_message(message.chat.id, f'Отпревлено {count} пользователям. =)')
            await state.finish()
        return count
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!! ФУНКЦИЯ БРОАДКАСТА IF SUDO
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ФУНКЦИЯ РЕДАКТОА СУБАДМИНОВ IF SUDO
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.callback_query_handler(text=['sub_admin_set'], user_id=thistuple.sudo)
async def handler_sudo_sub_admin_set(query: types.CallbackQuery):
    try:
        msg_del = await bot.send_message(query.from_user.id, f'Произведите действие с пользователями ...')
        asyncio.create_task(delete_message(msg_del, 2.2))
        messages_select_worcker = select_worcker()
        if len(messages_select_worcker) == 0:
            select_worcker_sql = "Нет данных."
        else:
            select_worcker_sql = '\n'.join([f'\n/user_id_{row[0]}\nЛогин: {row[1]}\nРоль: {row[2]}\nФИО: {row[3]}\nПодразделение: {row[4]}\nДата регистрации: {row[5]}\nДата изменения: {row[6]}\nСтатус: {row[7]}' for row in messages_select_worcker])
        await message.answer(f' Пользователи:\n {select_worcker_sql} \n')
    except:
        print(f"ФУНКЦИЯ РЕДАКТОА СУБАДМИНОВ IF SUDO")
    finally:
        logging.info(f"User {query.from_user.id} select all user's.")

@dp.message_handler(text_startswith=['/user_id'], user_id=thistuple.sudo)
async def text_startswith_sub_admin_set(message: types.Message):
    try:

        uset_select_worcker_id = select_worcker(user_id=message.text[9:])
        if len(uset_select_worcker_id) == 0:
            await message.answer(f'Такого пользователя нет, Вы что-то не то требуете. 😞')
        else:
            # Configure InlineKeyboardMarkup
            keyboard_sub_admin_set_full = types.InlineKeyboardMarkup()
            keyboard_sub_admin_set_full.add(types.InlineKeyboardButton(text='Enable', callback_data='menu_value_user_id_e_'+message.text[9:]))
            keyboard_sub_admin_set_full.add(types.InlineKeyboardButton(text='Disable', callback_data='menu_value_user_id_d_'+message.text[9:]))
            keyboard_sub_admin_set_full.add(types.InlineKeyboardButton(text='Message (Disable)', callback_data='menu_value_user_id_m_'+message.text[9:]))
            await message.answer(
                    md.text(
                        md.text(f'<b>ID user:</b> {uset_select_worcker_id[0][0]}'),
                        md.text(f'ФИО: {uset_select_worcker_id[0][3]}'),
                        md.text(f'Дата изменения: {uset_select_worcker_id[0][6]}'),
                        md.text(f'Статус: {uset_select_worcker_id[0][7]}'),
                        sep='\n',
                    ), reply_markup=keyboard_sub_admin_set_full
                    , parse_mode=types.ParseMode.HTML,
                )
    except:
        print(f"ФУНКЦИЯ РЕДАКТОА СУБАДМИНОВ IF SUDO222")
    finally:
        logging.info(f"User {message.from_user.id} edit user's {message.text[9:]}.")

# Обработчик кнопок действия над тикетом
@dp.callback_query_handler(text_contains='menu_value_user_id_')
async def menu_user_id(call: types.CallbackQuery):
    if call.data and call.data.startswith("menu_value_user_id_"):
        try:
            code = call.data[19]
            code_user_id = int(call.data[21:])
            if not code.isdigit():
                code = str(code)
            if code == 'e':
                set_create_worker_user_id(status='Enable', user_id=code_user_id)
                await call.message.edit_text(f'Пользователь №{code_user_id}\nпереведён в состояние Enable')
            if code == 'd':
                set_create_worker_user_id(status='Disable', user_id=code_user_id)
                await call.message.edit_text(f'Пользователь №{code_user_id}\nпереведён в состояние Disable')
            if code == 'm':
                await call.message.edit_text(f'Отправка сообщения пользователю. (позже)')
            else:
                await bot.answer_callback_query(call.id)
        except ValueError:
            await call.message.edit_text(f'Error except sql update.')
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ФУНКЦИЯ РЕДАКТОА СУБАДМИНОВ IF SUDO
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ФУНКЦИЯ РАСПРЕДЕЛЕНИЯ ticket
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.callback_query_handler(text=['ticket_select_worker'], user_id=thistuple.sudo)
@dp.callback_query_handler(text=['ticket_select_worker'], user_id=thistuple.sub_admin)
async def handler_ticket_select_worker(query: types.CallbackQuery):
    print (f'{query.data}')
    try:
        print('asdasdsss22222222')
        res_sub_admin_addr = sub_admin_addr(user_id=query.from_user.id)
        print (res_sub_admin_addr)
        if res_sub_admin_addr is None:
            print ('erererererer')
        else:
            try:
                res_sub_admin_ticket = sub_admin_select_ticket (res_sub_admin_addr=res_sub_admin_addr)
                res__ticket = '\n'.join([f'\n#/set_ticket{row[0]}\nКоротко:{row[1]}\nКому:{row[2]}\nСтатус:{row[3]}' for row in res_sub_admin_ticket])
                await bot.send_message(query.from_user.id, f' set_ticket\'s подразделения:\n {res__ticket} \n')
            except:
                print ("АЛЯРМ, запрос не получился2222")
                await bot.send_message(query.from_user.id, f' АЛЯРМ, запрос не получился2222')
    except:
        print ("АЛЯРМ, запрос не получился")
        await bot.send_message(query.from_user.id, f' ERROR ФУНКЦИЯ РАСПРЕДЕЛЕНИЯ ticket')
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ФУНКЦИЯ РАСПРЕДЕЛЕНИЯ ticket
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ВЫВОД ticket В ПОЛНОМ ВВИДЕ (ЕГО ПРОВЕРКА И ФУНКЦИИ)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.message_handler(text_startswith=['set_ticket'])
async def text_startswith_handler(message: types.Message):
    await message.answer(f'Вы ввели запрос без /, вроверьте данные и повторите попытку (/{message.text})')
    await message.answer(f'\U0001F31A')

# if the text starts with any string from the list
@dp.message_handler(text_startswith=['/set_ticket'])
async def text_startswith_handler(message: types.Message):
    #строим форму отоборажения полной заявки
    try:
        messages_task_full = select_task_full(user_id=message.from_user.id, task_id_pk=message.text[11:])
        #строим кнопки к форме отоборажения полной заявки
        try:
            create_button_users = select_users_ticket_addr(ticket_addr=messages_task_full[2])
            # Configure InlineKeyboardMarkup
            keyboard_create_button_users = types.InlineKeyboardMarkup()
            row_create_button_users = (types.InlineKeyboardButton(data2_cbu, callback_data="data_cbu_1#"+str(messages_task_full[0])+'_2#'+str(data1_cbu)) for data1_cbu, data2_cbu in create_button_users)
            keyboard_create_button_users.row(*row_create_button_users)
            keyboard_create_button_users.add(types.InlineKeyboardButton(text='Delete ticket', callback_data='menu_set_ticket_2'))
        except:
            print('ERROR ~480 строим кнопки к форме отоборажения полной заявки')
        if messages_task_full is not None:
            await message.answer(
                    md.text(
                        md.text('<b>#set_ticket</b>', messages_task_full[0]),
                        md.text('Коротко:', messages_task_full[1]),
                        md.text('Кому:', messages_task_full[2]),
                        md.text('Ваши данные:', messages_task_full[3]),
                        md.text('Ваш телефон:', messages_task_full[4]),
                        md.text('Ваша почта:', messages_task_full[5]),
                        md.text('Тескт задачи:', messages_task_full[6]),
                        md.text('Исполнитель:', messages_task_full[7]),
                        md.text('Дата подачи:', messages_task_full[8]),
                        md.text('Закрытие:', messages_task_full[9]),
                        md.text('Статус:', messages_task_full[10]),
                        sep="\n"
                    ),
                reply_markup=keyboard_create_button_users,
                parse_mode=types.ParseMode.HTML,
                )
        else:
            await message.answer(f'Заявки №{message.text[11:]} от Вас не было, вроверьте данные и повторите попытку')
    except:
        print ('ERROR ~600 строим форму отоборажения полной заявки')
    finally:
        logging.info(f"User {message.from_user.id} select full_ticket {message.text[11:]}.")  

# Обработчик кнопок действия над тикетом
@dp.callback_query_handler(text_contains='data_cbu_')
async def menu_data_cbu(call: types.CallbackQuery):
    if call.data and call.data.startswith("data_cbu_"):
        #Разложение по индексам
        try:
            data_cbu_index_1 = call.data.find("_1#")
            data_cbu_index_2 = call.data.find("_2#")
            #Выборка номеров ticket и users
            try:
                #индекс пользователя
                data_cbu_users = call.data[data_cbu_index_2+3:]
                #индекс заявки
                data_cbu_ticket = call.data[data_cbu_index_1+3:data_cbu_index_2]

            except:
                print ('ERROR индекс пользователя/заявки import')

        except:
            print ('ERROR index import')

        #sql-execute-users-ticket
        try:
            menu_data_cbu_update_ticket_users(data_cbu_users=data_cbu_users, data_cbu_ticket=data_cbu_ticket)
            res_select_users_name_from_id=select_users_name_from_id(user_id=data_cbu_users)
            await bot.send_message(call.from_user.id, f'Пользователь {res_select_users_name_from_id} прикреплён к заявке {data_cbu_ticket}')
            await bot.send_message(data_cbu_users, f'Вы прикреплены к заявке {data_cbu_ticket}')
        except:
            print ('ERROR sql-execute-users-ticket')
        finally:
            logging.info(f"User {query.from_user.id} edit user and ticket.")
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ВЫВОД ticket В ПОЛНОМ ВВИДЕ (ЕГО ПРОВЕРКА И ФУНКЦИИ)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ФУНКЦИЯ ВЫВОДА ticket
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.callback_query_handler(text='list_ticket')
async def inline_kb_answer_callback_handler_list_ticket(query: types.CallbackQuery):
    messages_task = select_task(user_id=query.from_user.id, limit=5)
    if len(messages_task) == 0:
        task_sql = "Нет данных."
    else:
        task_sql = '\n'.join([f'\n#/ticket{row[0]}\nКоротко:{row[1]}\nКому:{row[2]}\nСтатус:{row[3]}' for row in messages_task])
        count_task_user = count_task(user_id=query.from_user.id)
    await bot.send_message(query.from_user.id, f' Ваши ticket:\n {task_sql} \n\nВсего: {count_task_user}')
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ФУНКЦИЯ ВЫВОДА ticket
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ФОРМА ДИАЛОГА ВВОДА И РЕГИСТРАЦИИ ЗАЯВКИ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.message_handler(commands=['reg'], commands_prefix='!/')
@dp.callback_query_handler(text='reg_ticket')
async def inline_kb_answer_callback_handler_list_ticket(query: types.CallbackQuery):
    await Form.name_task.set()
    await bot.send_message(query.from_user.id, f'Напишите кратко задачу. \nДля отмены действий /cancel')

# Сюда приходит ответ с задачей (коротко)
@dp.message_handler(state=Form.name_task)
async def process_name_task(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name_task'] = message.text
    # переходим на следующий шаг
    await Form.next()
    # Configure ReplyKeyboardMarkup
    markup_name_task = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup_name_task.add(*thistuple.addr)
    await message.reply('Укажи подразделение (кнопкой)', reply_markup=markup_name_task)

# Проверяем подразделение
@dp.message_handler(lambda message: message.text not in thistuple.addr, state=Form.address_task)
async def process_address_task_invalid(message: types.Message):
    return await message.reply('Не знаю такого подразделения. Укажи подразделение кнопкой на клавиатуре')

# ввод направления
@dp.message_handler(state=Form.address_task)
async def process_address_task(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['address_task'] = message.text
    # переходим на следующий шаг
    await Form.next()
    await message.reply('Как к Вам обращаться?', reply_markup=types.ReplyKeyboardRemove())

# input name user
@dp.message_handler(state=Form.name_user)
async def process_address_task(message: types.Message, state: FSMContext):
    '''
    Process user name
    '''
    async with state.proxy() as data:
        data['name_user'] = message.text
    # переходим на следующий шаг
    await Form.next()
    await message.reply('Введите телефон')

# Проверяем телефон
@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.phone_user)
async def process_phone_user_invalid(message: types.Message):
    return await message.reply('Введите телефон или напишите для отмены /cancel')

@dp.message_handler(lambda message: message.text.isdigit(), state=Form.phone_user)
async def process_phone_user(message: types.Message, state: FSMContext):
    await state.update_data(phone_user=int(message.text))
    await Form.next()
#input mail
    await message.reply('Введите mail')

# Проверяем почту
@dp.message_handler(lambda message: not validate_email(message.text), state=Form.mail_user)
async def process_phone_user_mail(message: types.Message):
    return await message.reply('Введите электронную почту или для отмены /cancel')
    await bot.send_message(message.from_user.id, 'Всё отлично работает')

# input mail user
@dp.message_handler(state=Form.mail_user)
async def process_address_task(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['mail_user'] = message.text
    # переходим на следующий шаг
    await Form.next()
    await message.reply('Опишите задачу')

# input текста задачи и вывод конечного результата
@dp.message_handler(state=Form.text_task)
async def process_address_task(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text_task'] = message.text
        a_random = random.randint(0, 10)
        b_random = random.randint(0, 10)
        data['c_random'] = a_random+b_random
    await Form.next()
    await message.reply(f'Решите уравнение: {a_random}+{b_random}=?\nПроверка на робота.')

# input текста задачи и вывод конечного результата
@dp.message_handler(state=Form.test_task_finish)
async def process_address_task(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if int(message.text) == data['c_random']:
            await bot.send_message(
            message.chat.id,
            md.text(
                md.text('Вы подали заявку в,', md.bold(data['address_task'])),
                md.text('Коротко:', md.code(data['name_task'])),
                md.text('Ваш телефон:', data['phone_user']),
                md.text('Ваша почта:', data['mail_user']),
                md.text('Полный текст:', data['text_task']),
                md.text('You ID:', message.chat.id),
                sep='\n',
            ),
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
            )

            add_job(
                user_id=message.chat.id,
                first_name=message.from_user.username,
                name_task=data['name_task'],
                address_task=data['address_task'],
                name_user=data['name_user'],
                phone_user=data['phone_user'],
                mail_user=data['mail_user'],
                text_task=data['text_task'],
                )
            # Пишем в журнал
            logging.info(f'sql.execute active')
            await state.finish()

        else:
            await bot.send_message(message.chat.id, f'Вы неправильно решили уравнение.\nВы вписали: {message.text}')
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ФОРМА ДИАЛОГА ВВОДА И РЕГИСТРАЦИИ ЗАЯВКИ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ФОРМА ЗАЯВКИ ЗА МОДЕРАТОРСТВО ПОД ЗАЯВКАМИ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.callback_query_handler(text='create_worker')  # if cb.data == 'create_worker'
async def inline_kb_answer_callback_handler_create_worker(query: types.CallbackQuery):
    try:
        res_count_users = count_users(user_id=query.from_user.id)
        logging.info(f'users_count_{res_count_users}')
        if res_count_users == 0:
            await Form_worker_query.worker_query_agree.set()
            await bot.send_message(query.from_user.id, f'Вы собираетесь подать заявку на модератора по своему подразделению\nПодтвердите действие (кнопкой)\n /cancel для отмены действия', reply_markup=kb.agree)
        else:
            msg_create_worker = await bot.send_message(query.from_user.id, f'Вы уже подавали заявку. Удалите старую заявку, либо ожидайте.', reply_markup=kb.action_delete)
            asyncio.create_task(delete_message(msg_create_worker, 5.5))
            
    except:
        print(f"ERROR inline_kb_answer_callback_handler_create_worker")
    finally:
        logging.info(f"User {query.from_user.id} insert ticket is sub_admins.")

@dp.callback_query_handler(text = 'action_delete_tick_worker')
async def process_acion_delete_invalid(query: types.CallbackQuery):
    await bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
    delete_tick_worker(user_id=query.from_user.id)
    await bot.send_message(query.from_user.id, f'Удаление превыдущей заявки выполнено.')
    
@dp.message_handler(lambda message: message.text not in ["Согласен", "Не согласен"], state=Form_worker_query.worker_query_agree)
async def process_address_worker_agree_invalid(message: types.Message):
    return await message.reply("Мы не получили от Вас подтвердите или отказ, выбирите вариант на клавиатуре.")

# Ловим имя
@dp.message_handler(state=Form_worker_query.worker_query_agree)
async def process_name_worker_query_name(message: types.Message, state: FSMContext):

    if message.text == "Не согласен":
        await bot.send_message(message.chat.id, f'Ваш ответ: {message.text}\nОтменяем действие.', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
    elif message.text == "Согласен":
        async with state.proxy() as data:
            data['worker_query_agree'] = message.text
        # переходим на следующий шаг
        #await message.reply('приняли', reply_markup=types.ReplyKeyboardRemove())
        await message.reply(f'Укажи роль (кнопкой)', reply_markup=kb.role)
        await Form_worker_query.next()
    else:
        await bot.send_message(message.chat.id, f'Вы что-то не то нажимаете, а именно |{message.text}|.')

@dp.message_handler(lambda message: message.text not in ["Распределение", "Выполнение"], state=Form_worker_query.worker_query_role)
async def process_worker_role_invalid(message: types.Message):
    return await message.reply("Мы не получили от Вас подходящую роль, выбирите вариант на клавиатуре.")

# input
@dp.message_handler(state=Form_worker_query.worker_query_role)
async def process_role(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['worker_query_role'] = message.text
    await message.reply('Как к Вам обращаться?', reply_markup=types.ReplyKeyboardRemove())
    await Form_worker_query.next()

# input name user
@dp.message_handler(state=Form_worker_query.worker_query_name)
async def process_address_task(message: types.Message, state: FSMContext):
    '''
    Process user name
    '''
    async with state.proxy() as data:
        data['worker_query_name'] = message.text
    # переходим на следующий шагавочно (пото
    await Form_worker_query.next()
    # Configure ReplyKeyboardMarkup
    markup_name_task = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup_name_task.add(*thistuple.addr)
    await message.reply('Укажи подразделение (кнопкой)', reply_markup=markup_name_task)

# Проверяем подразделение
@dp.message_handler(lambda message: message.text not in thistuple.addr, state=Form_worker_query.worker_query_addr)
async def process_address_worker_addr_invalid(message: types.Message):
    return await message.reply('Не знаю такого подразделения. Укажи подразделение кнопкой на клавиатуре')

# Ловим ответ пользователя о создании модераторства
@dp.message_handler(state=Form_worker_query.worker_query_addr)
async def process_name_worker_query_agree(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['worker_query_addr'] = message.text
    # переходим на следующий шаг
    await Form_worker_query.next()
    await bot.send_message(
        message.chat.id,
        md.text(
            md.text('Проверьте данные на корректность. В случае некорректности нажмите /cancel и повторите заявку'),
            md.text('Для подтвеждения наберите', md.code('команду'), 'yes'),
            md.text('Ваш ID', message.chat.id),
            md.text('Ваш логин:', message.from_user.username),
            md.text('На обработку информации:', data['worker_query_agree']),
            md.text('ФИО:', md.bold(data['worker_query_name'])),
            md.text('Подразделение:', md.code(data['worker_query_addr'])),
            sep='\n',
        ), reply_markup=kb.action_yes_no,
         parse_mode=types.ParseMode.MARKDOWN,
    )

@dp.callback_query_handler(state=Form_worker_query.worker_query_confirm)
async def worker_query_confirm_end(query: types.CallbackQuery, state: FSMContext):
    if query.data == 'action_yes':
        async with state.proxy() as data:
            await bot.send_message(query.from_user.id, f'Заявка отправлена, ожидайте одобрения.', reply_markup=types.ReplyKeyboardRemove())
            add_create_worker(
                user_id=query.from_user.id,
                first_name=query.from_user.username,
                worker_query_role=data['worker_query_role'],
                worker_query_name=data['worker_query_name'],
                worker_query_addr=data['worker_query_addr'],
                )
            # Пишем в журнал
            logging.info(f'sql.execute active')
            # Finish conversation
            await state.finish()
    elif query.data == 'action_no':
        async with state.proxy() as data:
            logging.info('Cancelling state')
            # Cancel state and inform user about it
            await state.finish()
            # And remove keyboard (just in case)                                                                           
            await bot.send_message(query.from_user.id, f'Cancelling state.', reply_markup=types.ReplyKeyboardRemove())
    else:
        await bot.send_message(query.from_user.id, f'User insert error-data.')
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ФОРМА ЗАЯВКИ ЗА МОДЕРАТОРСТВО ПОД ЗАЯВКАМИ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ОТВЕТ НА НЕИЗВЕСТНЫЕ КОМАНДЫ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@dp.message_handler()
async def echo_message(message: types.Message, commands_prefix='!/'):
    # Пишем в журнал
    logging.info(f'logger input text: {message.from_user.id} {message.text}')
    await message.answer(message.text)
    message_text_echo = text('Я не знаю, что с этим делать ....',
                        italic('Я просто напомню,что есть'),
                        code('команда /help'),
                        code('команда /menu'),
                        sep="\n")
    await message.reply(message_text_echo, parse_mode=ParseMode.MARKDOWN)
    await bot.send_message(message.from_user.id, '\U0001F636')
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! ОТВЕТ НА НЕИЗВЕСТНЫЕ КОМАНДЫ
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#РЕГИСТРАЦИЯ КОМАНД, ОТОБРАЖАЕМЫХ В ИНТЕРФЕЙСЕ TELEGRAM
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command='/start', description='Запуск и перезапуск бота'),
        types.BotCommand(command='/reg', description='Регистрация задачи'),
        types.BotCommand(command='/menu', description='Возможные команды'),
        types.BotCommand(command='/help', description='Возможности бота'),
        types.BotCommand(command='/my_task', description='Мои задачи'),
        types.BotCommand(command='/cancel', description='Отменить текущее действие')
    ]
    await dp.bot.set_my_commands(commands)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#КОНЕЦ!!! РЕГИСТРАЦИЯ КОМАНД, ОТОБРАЖАЕМЫХ В ИНТЕРФЕЙСЕ TELEGRAM
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ТЕЛО ОСНОВА PYTHON-CODE
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
async def main():
    # Включим ведение журнала
    formatter = '[%(asctime)s] %(levelname)8s --- - %(name)s -%(message)s (%(filename)s:%(lineno)s)'
    logging.basicConfig(
        # TODO раскомментировать на сервере
        #filename=f'bot-from-{datetime.datetime.now().date()}.log',
        #filemode='w',
        #format=formatter,
        #datefmt='%Y-%m-%d %H:%M:%S',
        # TODO logging.WARNING
        level=logging.INFO
    )

    logging.warning('Starting bot')

    # Установка команд бота
    await set_commands(bot)

    # Запуск поллинга
    await dp.skip_updates()  # пропуск накопившихся апдейтов (необязательно)
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#ТЕЛО ОСНОВА PYTHON-CODE
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
