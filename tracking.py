import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, Text
from aiogram.dispatcher.filters.state import State, StatesGroup
import random
import string
import logging

class Form(StatesGroup):
    order_number = State()  # for adding and viewing orders
    tracking_number = State()  # for adding and viewing orders
    delete_orders = State()  # for deleting orders
    username = State()  # for capturing username
    edit_username = State()  # for editing usernames
    new_tracking = State()  # for capturing new tracking number

API_TOKEN = '6391090777:AAHkSylx4KF5woW5rFfMQ-Dy7fecaCd2qho'
ADMIN_ID = 1715411908

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

async def on_startup(dp):
    async with aiosqlite.connect('track.db') as db:
        cursor = await db.cursor()
        await cursor.execute("CREATE TABLE IF NOT EXISTS orders (order_number text, tracking_number text)")
        await db.commit()
    await bot.send_message(ADMIN_ID, 'Bot has been started')

async def on_shutdown(dp):
    await bot.send_message(ADMIN_ID, 'Bot has been stopped')
#Start command Handler

@dp.message_handler(Command('start'))
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Generate Order", "Edit Tracking", "Check Tracking", "View All Orders", "Delete Orders", "Edit Username"]
        keyboard.add(*buttons)
        await message.answer('Please choose:', reply_markup=keyboard)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Check Tracking"]
        keyboard.add(*buttons)
        await message.answer('Please choose:', reply_markup=keyboard)

  #Generate Order Command Handler
@dp.message_handler(Text(equals='Generate Order'))
async def generate_order(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await Form.username.set()  # set state to capture username
        await message.answer('Please enter the username for the new order:')
    else:
        await message.answer('You are not the admin.')

#Edit Tracking Command Handler
@dp.message_handler(Text(equals='Edit Tracking'))
async def edit_tracking(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await Form.order_number.set()
        await state.update_data(edit=True, check=False, edit_username=False)  # to indicate we're in edit mode
        await message.answer('Please enter the order number:')
    else:
        await message.answer('You are not the admin.')



# Check Tracking Command Handler
@dp.message_handler(Text(equals='Check Tracking'))
async def check_tracking(message: types.Message, state: FSMContext):
    await Form.order_number.set()
    await state.update_data(check=True)  # to indicate we're in check mode
    await message.answer('Please enter the order number:')

#delete orders command handler
@dp.message_handler(Text(equals='Delete Orders'))
async def delete_orders(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await Form.delete_orders.set()
        await message.answer('Please enter the order number(s) separated by comma:')
    else:
        await message.answer('You are not the admin.')
#edit username command handler
@dp.message_handler(Text(equals='Edit Username'))
async def edit_username(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await Form.order_number.set()
        await message.answer('Please enter the order number:')
        await state.update_data(edit_username=True)  # to indicate we're in edit username mode
    else:
        await message.answer('You are not the admin.')

@dp.message_handler(state=Form.delete_orders)
async def process_delete_orders(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        order_numbers = [num.strip() for num in message.text.split(',')]
        deleted_orders = []
        non_existing_orders = []

        async with aiosqlite.connect('track.db') as db:
            cursor = await db.cursor()
            for order_number in order_numbers:
                await cursor.execute("SELECT * FROM orders WHERE order_number=?", (order_number,))
                row = await cursor.fetchone()
                if row is None:
                    non_existing_orders.append(order_number)
                else:
                    await cursor.execute("DELETE FROM orders WHERE order_number=?", (order_number,))
                    await db.commit()
                    deleted_orders.append(order_number)

        if non_existing_orders:
            await message.answer(f"These order numbers do not exist: {', '.join(non_existing_orders)}\nPlease provide existing order numbers:")
        else:
            await message.answer(f'Order(s) {", ".join(deleted_orders)} deleted successfully.')
            await state.finish()
#capture username
@dp.message_handler(state=Form.username)
async def process_username(message: types.Message, state: FSMContext):
    username = message.text
    order_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    async with aiosqlite.connect('track.db') as db:
        cursor = await db.cursor()
        await cursor.execute("INSERT INTO orders VALUES (?, '', ?)", (order_number, username,))
        await db.commit()
    await message.answer(f'Your order number is: {order_number} Please use @daydreamtracksbot to check the tracking for your order at least 48 hours from order placed. Thank you so much! Your order will be processed and shipped soon.')
    await state.finish()  # reset the state
  #view all orders
@dp.message_handler(Text(equals='View All Orders'))
async def view_all_orders(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        async with aiosqlite.connect('track.db') as db:
            cursor = await db.cursor()
            await cursor.execute("SELECT * FROM orders")
            all_orders = await cursor.fetchall()
        if all_orders:
            for order in all_orders:
                await message.answer(f'Order Number: {order[0]}, Tracking Number: {order[1]}, Username: {order[2]}')
        else:
            await message.answer('No orders are currently available.')
    else:
        await message.answer('You are not the admin.')

@dp.message_handler(state='*', commands='cancel')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    await message.answer('Cancelled.')

#edit username command handler
@dp.message_handler(state=Form.new_username)
async def process_new_username(message: types.Message, state: FSMContext):
    new_username = message.text
    async with aiosqlite.connect('track.db') as db:
        cursor = await db.cursor()
        data = await state.get_data()
        order_number = data['order_number']
        await cursor.execute(f"UPDATE orders SET username = '{new_username}' WHERE order_number = '{order_number}'")
        await db.commit()

    await message.answer(f"Username for order {order_number} has been updated to {new_username}.")
    await state.finish()

@dp.message_handler(commands='edit_username')
async def start_editing_username(message: types.Message, state: FSMContext):
    await Form.order_number.set()
    await state.update_data({'edit_username': True})
    await message.answer('Please enter the order number:')



@dp.message_handler(state=Form.order_number)
async def process_order_number(message: types.Message, state: FSMContext):
    order_number = message.text.upper()
    data = await state.get_data()
    data['order_number'] = order_number
    await state.update_data(data)

    async with aiosqlite.connect('track.db') as db:
        cursor = await db.cursor()
        await cursor.execute(f"SELECT * FROM orders WHERE order_number='{order_number}'")
        order = await cursor.fetchone()

    if data.get('check_tracking'):
        if order:
            await message.answer(f"The tracking number for order {order_number} is {order[1]}.")
        else:
            await message.answer(f"No order found with the number {order_number}.")
        await state.finish()

    elif data.get('edit_username'):
        if order:
            await Form.new_username.set()  # Set the next state
            await message.answer('Please enter the new username:')
        else:
            await message.answer(f"No order found with the number {order_number}.")
            await state.finish()


    #process new tracking
@dp.message_handler(state=Form.new_tracking)
async def process_new_tracking(message: types.Message, state: FSMContext):
    new_tracking_number = message.text.upper()
    data = await state.get_data()
    order_number = data.get('order_number', None)

    if order_number:
        async with aiosqlite.connect('track.db') as db:
            cursor = await db.cursor()
            await cursor.execute(f"UPDATE orders SET tracking_number='{new_tracking_number}' WHERE order_number='{order_number}'")
            await db.commit()

        await message.answer(f"Tracking number for order {order_number} updated successfully.")
    else:
        await message.answer("Could not find the order number to update.")

    await state.finish()






@dp.message_handler(state=Form.tracking_number)
async def process_tracking_number(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        async with aiosqlite.connect('track.db') as db:
            cursor = await db.cursor()
            await cursor.execute("UPDATE orders SET tracking_number=? WHERE order_number=?", (message.text, data['order_number']))
            await db.commit()
        await message.answer(f'Tracking number for {data["order_number"]} updated to {message.text}')
    await state.finish()
if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)
