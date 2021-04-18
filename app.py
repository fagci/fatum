#!/usr/bin/env python3
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
    distance = Required(int, default=1000)


@db_session
def get_user(uid):
    try:
        return UserSetting[uid]
    except ObjectNotFound:
        return UserSetting(id=uid)


@client.on_message(filters.location)
def loc(c: Client, m: Message):
    uid = m.from_user.id
    u = get_user(uid)

    loc: Location = m.location
    p = Point(loc.latitude, loc.longitude)
    try:
        d = qr.randint(500, u.distance) / 1000
        angle = qr.randint(0, 360)
        np = distance.distance(d).destination(p, angle)
        m.reply_location(np.latitude, np.longitude)
    except:
        m.reply('Error =(')


@db_session
def change_distance(m: Message, val: str):
    d = 0
    if val:
        try:
            d = int(val)
        except:
            m.reply('Wrong value')
            return

    u = get_user(m.from_user.id)
    if d:
        u.distance = d
    else:
        d = u.distance
    m.reply('Distance: %d' % d)


@client.on_message(filters.regex(r'^\d+'))
def dist(c: Client, m: Message):
    change_distance(m, m.text)


@client.on_message(filters.command('distance'))
def dist(c: Client, m: Message):
    change_distance(m, m.text[len('/distance'):])


db.bind(provider='sqlite', filename='db.sqlite', create_db=True)
db.generate_mapping(create_tables=True)


client.start()

idle()

client.stop()
