from aiogram import Dispatcher, Bot, executor
from aiogram.types import Message, CallbackQuery, LabeledPrice
from dotenv import load_dotenv
from keyboards import *
from work import *
import os

load_dotenv()

bot = Bot(token=os.getenv('TOKEN'))
PAYMENT = os.getenv('PAYMENT')

dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def command_start(message: Message):
    chat_id = message.chat.id
    """Надо попробовать вытащить пользователя из базы
    Если его нет - начать регистраци
    Если он есть - показать главное меню"""
    user = first_select_user(chat_id)
    if user:
        await message.answer('Авторизация прошла успешно')
        await main_menu(message)
    else:
        text = f'''Здравствуйте, {message.from_user.full_name},
Вас приветствует бот PROWEB-ЕДА. Для продолжения зарегестрируйтесь
Отправив свой контакт 👇👇👇'''
        await message.answer(text, reply_markup=generate_phone_number())


@dp.message_handler(content_types=['contact'])
async def register(message: Message):
    chat_id = message.from_user.id
    full_name = message.from_user.full_name
    phone = message.contact.phone_number
    register_user(chat_id, full_name, phone)
    create_cart(chat_id)
    await message.answer('Регистрация прошла успешно')
    await main_menu(message)


async def main_menu(message: Message):
    await message.answer('Здравствуйте, выберите, что хотите сделать',
                         reply_markup=generate_main_menu())


#@dp.message_handler(regexp=r'✅ Сделать заказ')
@dp.message_handler(lambda message: '✅ Сделать заказ' in message.text)
async def make_order(message: Message):
    categories = get_categories()
    await message.answer('Выберите категорию: ',
                         reply_markup=generate_categories(categories))

# category_1

@dp.callback_query_handler(lambda call: 'category' in call.data)
async def show_products_by_category(call: CallbackQuery):
    _, category_id = call.data.split('_')
    products = get_products_by_category(category_id)
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    await bot.edit_message_text(text='Выберите продукт: ',
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=generate_products(products))

@dp.callback_query_handler(lambda call: 'product' in call.data)
async def product_detail(call: CallbackQuery):
    _, product_id = call.data.split('_')
    product_id = int(product_id)
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    product = get_product(product_id)
    print(product)
    await bot.delete_message(chat_id, message_id)
    with open(product[5], mode='rb') as img:
        caption = f'''{product[2]}

Описание: {product[4]}

Цена: {product[3]}

Выбрано: 1 - {product[3]}'''
        await bot.send_photo(chat_id=chat_id,
                             photo=img,
                             caption=caption,
                             reply_markup=generate_detail_product(product[0], product[1]))

@dp.callback_query_handler(lambda call: 'change' in call.data)
async def change_quantity(call: CallbackQuery):
    _, product_id, quantity = call.data.split('_')
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    product = get_product(product_id)
    caption = f'''{product[2]}

Описание: {product[4]}

Цена: {product[3]}

Выбрано: {quantity} - {product[3] * int(quantity)} сум'''
    if int(quantity) >= 1:
        await bot.edit_message_caption(chat_id=chat_id,
                                       message_id=message_id,
                                       caption=caption,
                                       reply_markup=generate_detail_product(product[0], product[1], int(quantity)))


@dp.callback_query_handler(lambda call: 'main_menu' in call.data)
async def to_main_menu(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    categories = get_categories()
    await bot.edit_message_text(text='Выберите категорию: ',
                                chat_id=chat_id,
                                message_id=message_id,
                                reply_markup=generate_categories(categories))


@dp.callback_query_handler(lambda call: 'back' in call.data)
async def back_to_category(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    await bot.delete_message(chat_id, message_id)
    _, category_id = call.data.split('_')
    products = get_products_by_category(category_id)
    await bot.send_message(chat_id, 'Выберите продукт: ',
                           reply_markup=generate_products(products))


@dp.callback_query_handler(lambda call: call.data.startswith('cart'))
async def add_product_to_cart(call: CallbackQuery):
    chat_id = call.message.chat.id
    # cart_1_2   - cart - product_id = 1 -  quantity = 2
    _, product_id, quantity = call.data.split('_')
    product_id, quantity = int(product_id), int(quantity)

    """Вытащить id корзины пользователя"""
    cart_id = get_cart_id(chat_id)

    """Получим информацию о товаре по его id"""
    product = get_product(product_id)
    product_name, price = product[2], product[3]
    final_price = quantity * price

    if insert_or_update_cart_product(cart_id, product_name, quantity, final_price):
        await bot.answer_callback_query(call.id, text='Продукт успешно добавлен')
    else:
        await bot.answer_callback_query(call.id, text='Количество успешно изменено')


@dp.message_handler(lambda message: '🛒 Корзина' in message.text)
async def show_cart(message: Message, edit_message=False):
    chat_id = message.chat.id
    """Получить id корзины"""
    cart_id = get_cart_id(chat_id)
    """Обновить данные общей суммы и количества корзины"""
    update_total_price_quantity(cart_id)
    """Вывести всю общую сумму и общее количество из корзины"""
    total_products, total_price = get_total_products_price(cart_id)
    """Вывести все строчки в корзине"""
    cart_products = get_cart_products(cart_id)
    """Отправить сообщение пользователю"""
    print(total_products, total_price)
    print(cart_products)

    text = 'Ваша корзина\n\n'
    i = 0
    for product in cart_products:
        i += 1
        text += f'''{i}. {product[2]}
Количество: {product[3]}
Общая стоимость: {product[4]}\n\n'''

    text += f'''Общее количество продуктов: {0 if total_products is None else total_products}
Общая стоимость корзины: {0 if total_price is None else total_price}'''

    if edit_message: # True
        await bot.edit_message_text(text, chat_id, message.message_id,
                                    reply_markup=generate_cart_buttons(cart_id, cart_products))
    else:
        await bot.send_message(chat_id, text, reply_markup=generate_cart_buttons(cart_id, cart_products))


@dp.callback_query_handler(lambda call: 'delete' in call.data)
async def delete_cart_product(call: CallbackQuery):
    message = call.message
    _, cart_product_id = call.data.split('_')
    cart_product_id = int(cart_product_id)

    delete_from_database(cart_product_id)

    await bot.answer_callback_query(call.id, text='Продукт успешно удален')
    await show_cart(message, edit_message=True)

@dp.callback_query_handler(lambda call: 'edit' in call.data)
async def edit_quantity_cart_products(call: CallbackQuery):
    _, cart_product_id, quantity = call.data.split('_')
    cart_product_id, quantity = int(cart_product_id), int(quantity)
    if quantity == 0:
        delete_from_database(cart_product_id)
    else:
        edit_quantity_in_database(cart_product_id, quantity)
    await show_cart(message=call.message, edit_message=True)


@dp.callback_query_handler(lambda call: 'order' in call.data)
async def create_order(call: CallbackQuery):
    chat_id = call.message.chat.id
    _, cart_id = call.data.split('_')
    cart_id = int(cart_id)
    """Вывести всю общую сумму и общее количество из корзины"""
    total_products, total_price = get_total_products_price(cart_id)
    """Вывести все строчки в корзине"""
    cart_products = get_cart_products(cart_id)
    """Отправить сообщение пользователю"""
    print(total_products, total_price)
    print(cart_products)

    text = 'Ваш Заказ\n\n'
    i = 0
    for product in cart_products:
        i += 1
        text += f'''{i}. {product[2]}
Количество: {product[3]}
Общая стоимость: {product[4]}\n\n'''

    text += f'''Общее количество продуктов: {0 if total_products is None else total_products}
Общая стоимость заказа: {0 if total_price is None else total_price}'''

    await bot.send_invoice(
        chat_id=chat_id,
        title=f'Заказ №{cart_id}',
        description=text,
        payload='bot-defined invoice payload',
        provider_token=PAYMENT,
        currency='UZS',
        prices=[
            LabeledPrice(label='Общая стоимость', amount=int(total_price * 100)),
            LabeledPrice(label='Доставка', amount=1500000)
        ]
    )
    await bot.send_message(chat_id, 'Заказ оплачен!')

executor.start_polling(dp)


"""Создать таблицу заказов, отправлять в канал или группу сообщение о заказе после оплаты
Для менеджеров. И у таблицы заказов должно быть поле СТАТУС (готовится, едет, принят)
И оно должно меняться по нажатию на кнопку админом

Сделать админку, для добавления новых товаров и категорий, прямо из бота"""












