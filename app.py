#!/usr/bin/env python3
from datetime import datetime

from geopy import distance
from geopy.point import Point
from pony.orm import Database, db_session
from pony.orm.core import ObjectNotFound, PrimaryKey, Required
from pyrogram import Client, filters, idle
from pyrogram.types import Location, Message
import quantumrandom as qr

client = Client('session')

db = Database()


class UserSetting(db.Entity):
    id = PrimaryKey(int)
    distance = Required(int, default=3000)
    created_at = Required(datetime, default=datetime.utcnow())
    updated_at = Required(datetime, default=datetime.utcnow())
    points_count = Required(int, default=0)


@db_session
def get_user(uid):
    try:
        u = UserSetting[uid]
    except ObjectNotFound:
        u = UserSetting(id=uid)
    return u


@db_session
def update_points_count(uid):
    u = UserSetting[uid]
    u.points_count += 1
    u.updated_at = datetime.utcnow()


@client.on_message(filters.location)
def loc(c: Client, m: Message):
    m.reply_chat_action('find_location')
    uid = m.from_user.id
    u = get_user(uid)

    loc: Location = m.location
    p = Point(loc.latitude, loc.longitude)
    try:
        d = qr.randint(500, u.distance) / 1000
        angle = qr.randint(0, 360)
        np = distance.distance(d).destination(p, angle)
        m.reply_location(np.latitude, np.longitude)
        c.send_message(m.from_user.id, 'В добрый путь!')
        update_points_count(uid)
    except Exception as e:
        m.reply('Error =(\n%s' % e)


@db_session
def change_distance(m: Message, val: str):
    d = 0
    if val:
        try:
            d = int(val)
            if d <= 0 or d > 20_000_000:
                raise ValueError
        except:
            m.reply('Wrong value')
            return

    u = get_user(m.from_user.id)
    if d:
        u.distance = d
        u.updated_at = datetime.utcnow()
    else:
        d = u.distance
    m.reply('Дистанция: %d м' % d)


@client.on_message(filters.regex(r'^\d+'))
def dist(c: Client, m: Message):
    change_distance(m, m.text)


@client.on_message(filters.command('distance'))
def dist(c: Client, m: Message):
    change_distance(m, m.text[len('/distance'):])


@client.on_message(filters.command(['start', 'help']))
def dist(c: Client, m: Message):
    u = get_user(m.from_user.id)
    m.reply((
        '🙋 Добро пожаловать в ваш Фатум!\n\n'
        'Дистанция генерации: %d м.\n\n'
        'Отправьте местоположение '
        'для генерации новой точки '
        'или отправьте желаемую дистанцию в метрах.'
    ) % (u.distance))


db.bind(provider='sqlite', filename='db.sqlite', create_db=True)
db.generate_mapping(create_tables=True)


client.start()

idle()

client.stop()
