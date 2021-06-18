#!/usr/bin/env python3
from datetime import datetime

from dateutil.tz import tzlocal
from dateutil.tz.tz import tzutc
from geopy import distance
from geopy.point import Point
from pony.orm import Database, db_session
from pony.orm.core import ObjectNotFound, Optional, PrimaryKey, Required, select, desc
from pyrogram import Client, filters
from pyrogram.types import Location, Message
from pyrogram.types.user_and_chats.user import User
import quantumrandom as qr

ADMIN_ID = 202242124

client = Client('session')

db = Database()


class UserSetting(db.Entity):
    id = PrimaryKey(int)
    username = Optional(str)
    distance = Required(int, default=3000)
    created_at = Required(datetime, default=datetime.utcnow)
    updated_at = Required(datetime, default=datetime.utcnow)
    points_count = Required(int, default=0)


@db_session
def get_user(user: User) -> UserSetting:
    try:
        u = UserSetting[user.id]
        if not u.username and user.username:
            u.username = user.username
    except ObjectNotFound:
        u = UserSetting(id=user.id, username=user.username or '')
    return u


@db_session
def update_points_count(user: User):
    u = UserSetting[user.id]
    u.points_count += 1
    u.updated_at = datetime.utcnow()


@db_session
def change_distance(user: User, val: str):
    d = None
    u = get_user(user)
    od = u.distance

    if val:
        try:
            d = int(val)
        except:
            pass

    if d is None or d <= 0 or d > 20_000_000:
        return od

    u.distance = d
    u.updated_at = datetime.utcnow()

    return d


@client.on_message(filters.regex(r'^\d+'))
def dist(_: Client, m: Message):
    d = change_distance(m.from_user, m.text)
    m.reply('Дистанция: %d м' % d)


@client.on_message(filters.command('distance'))
def dist_cmd(_: Client, m: Message):
    """old variant with distance set"""
    d = change_distance(m.from_user, m.text[len('/distance'):])
    m.reply('Дистанция: %d м' % d)


@client.on_message(filters.command(['start', 'help']))
def help(_: Client, m: Message):
    u = get_user(m.from_user)
    m.reply((
        '🙋 Добро пожаловать в ваш Фатум!\n\n'
        'Дистанция генерации: %d м.\n\n'
        'Отправьте местоположение '
        'для генерации новой точки '
        'или отправьте желаемую дистанцию в метрах.'
    ) % (u.distance))


@client.on_message(filters.location)
def loc(c: Client, m: Message):
    m.reply_chat_action('find_location')
    user = m.from_user
    u = get_user(user)

    loc: Location = m.location
    p = Point(loc.latitude, loc.longitude)
    try:
        d = qr.randint(500, u.distance) / 1000
        angle = qr.randint(0, 360)
        np = distance.distance(d).destination(p, angle)
        m.reply_location(np.latitude, np.longitude)
        c.send_message(m.from_user.id, 'В добрый путь!')
        update_points_count(user)
    except Exception as e:
        m.reply('Error =(\n%s' % e)


@db_session
def get_stats():
    total = UserSetting.select().count()
    users = select((u.updated_at, u.points_count, u.username, u.id)
                   for u in UserSetting).order_by(lambda u, p, n, i: desc(u)).limit(10)
    return ('Total: %s\n\n' % total) + '\n'.join(
        (
            '`%s %s` %s' % (
                upd.replace(tzinfo=tzutc()).astimezone(
                    tzlocal()).strftime('%d.%m.%y %H:%M'),
                pc,
                ('@%s' % un) if un else uid,
            )
        ) for upd, pc, un, uid in users
    )


@ client.on_message(filters.command('stats') & filters.chat(ADMIN_ID))
def stats(_: Client, m: Message):
    m.reply_text(get_stats())


db.bind(provider='sqlite', filename='db.sqlite', create_db=True)
db.generate_mapping(create_tables=True)


client.run()
