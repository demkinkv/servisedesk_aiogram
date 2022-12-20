import asyncio
import re
from .chat_dispatcher import ChatDispatcher
import logging
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN ='1873069944:AAH1HnAPM-L4xNkfigNDc5L6153bmFt7pRs'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

async def chat(get_message):
    try:
        message = await get_message()
        await message.answer('Умею складывать числа, введите первое число')

        first = await get_message()
        if not re.match('^\d+$', str(first.text)):
            await first.answer('это не число, начните сначала: /start')
            return

        await first.answer('Введите второе число')
        second = await get_message()

        if not re.match('^\d+$', str(second.text)):
            await second.answer('это не число, начните сначала: /start')
            return

        result = int(first.text) + int(second.text)
        await second.answer('Будет %s (/start - сначала)' % result)

    except ChatDispatcher.Timeout as te:
        await te.last_message.answer('Что-то Вы долго молчите, пойду посплю')
        await te.last_message.answer('сначала - /start')

chat_dispatcher = ChatDispatcher(chatcb=chat,
                                 inactive_timeout=20)

@dp.message_handler()
async def message_handle(message: types.Message):
    await chat_dispatcher.handle(message)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)