from datetime import datetime

from typing import Union

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from aiogram.types import Message
from sqlalchemy.orm import selectinload

from models import User
from data.config import ADMINS


async def db_add_to_db(item, message: Message, session: AsyncSession):
    """Добавление сущности в бд"""
    
    session.add(item)
    try:
            
        await session.commit()
        await session.refresh(item)
        return item
    except IntegrityError as ex:
        await session.rollback()
        await message.answer('Произошла ошибка.')
        await message.answer(ex)
        return None


async def db_delete_item(item, session: AsyncSession):
    """ удаление сущности из бд"""

    try:
        await session.delete(item)
        await session.commit()
    except IntegrityError:
        await session.rollback()


async def db_get_items(model, message: Message, session: AsyncSession):
    """Получение всех сущностей модели"""

    sql = select(model)
    items_sql = await session.execute(sql)
    items = items_sql.scalars().all()
    return items

async def get_item(model, field: str, value, message: Message, session: AsyncSession):
    """
    Получить сущность из базы данных по любому полю.

    :param model: Модель (класс) SQLAlchemy.
    :param field: Поле модели для фильтрации.
    :param value: Значение поля для поиска.
    :param message: Объект для отправки сообщений в бота
    :param session: Сессия SQLAlchemy для выполнения запроса.
    :return: Найденная сущность или None.
    """
    try:
        # Получаем атрибут модели по имени поля
        column = getattr(model, field)
        
        # Выполняем запрос с фильтрацией по полю
        result = await session.execute(
            select(model).where(column == value).options(selectinload("*"))
        )
        return result.scalars().first()
    
    except AttributeError:
        # Если поле не существует в модели
        await message.answer("Произошла ошибка!")
        print(f"Поле '{field}' не существует в модели {model.__name__}")
        return False
    
    except IntegrityError:
        await message.answer("Произошла ошибка!")
        print(f"Ошибка в подключении к бд")
        return False

async def db_get_item_by_id(model, id: int, message: Message, session: AsyncSession):
    """Получение сущности модели"""

    sql = select(model).where(model.id == id)
    item_sql = await session.execute(sql)
    item = item_sql.scalars().first()
    return item

async def update_item(model, pk: int, update_data: dict, message: Message, session: AsyncSession):
    """Обновление сущности в бд"""

    stmt = (
        update(model)  # Указываем модель
        .where(model.id == pk)  # Условие: обновить запись с указанным ID
        .values(**update_data)  # Передаем данные для обновления
        .execution_options(synchronize_session="fetch")  # Синхронизация сессии
    )
    # Выполняем запрос
    await session.execute(stmt)

    try:
        # Подтверждаем изменения
        await session.commit()
        return True
    except IntegrityError:        
        await session.rollback()
        return False
    
async def get_field_values(model, field, message: Message, session: AsyncSession):
    """
    Получить значения определенного поля модели из базы данных.

    :param model: Модель (класс) SQLAlchemy.
    :param field: Поле модели, значения которого нужно получить.
    :param message: Объект для отправки сообщений в бота
    :param session: Сессия SQLAlchemy для выполнения запроса.
    :return: Список значений поля.
    """
    try:
        column = getattr(model, field)
        result = await session.execute(select(column))
        return result.scalars().all()
    
    except AttributeError:
        # Если поле не существует в модели
        await message.answer("Произошла ошибка!")
        print(f"Поле '{field}' не существует в модели {model.__name__}")
        return False
    
async def get_field_value(model, pk: int, field, message: Message, session: AsyncSession):
    """
    Получить значения определенного поля модели из базы данных.

    :param model: Модель (класс) SQLAlchemy.
    :param field: Поле модели, значения которого нужно получить.
    :param message: Объект для отправки сообщений в бота
    :param session: Сессия SQLAlchemy для выполнения запроса.
    :return: Список значений поля.
    """
    try:
        column = getattr(model, field)
        result = await session.execute(select(column).where(model.id == pk))
        return result.scalars().first()
    
    except AttributeError:
        # Если поле не существует в модели
        await message.answer("Произошла ошибка!")
        print(f"Поле '{field}' не существует в модели {model.__name__}")
        return False

async def db_register_user(message: Message, session: AsyncSession):
    """регистрация юзера"""
    if str(message.from_user.id) in ADMINS:
        user = User(tg_id=int(message.from_user.id), is_admin=True, datetime_register=datetime.now())
    else:
        user = User(tg_id=int(message.from_user.id), datetime_register=datetime.now())
    
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
        return True
    except IntegrityError:
        await message.answer("Произошла ошибка при регистрации пользователя!")
        await session.rollback()
        return False
    

async def db_get_all_users(message: Message, session: AsyncSession):
    """ получение всех юзеров """

    users = await db_get_items(User, message, session)
    
    users_list = '\n'.join([f'{index+1}. {item.tg_id}' for index, item in enumerate(users)])    
    
    return users_list
    