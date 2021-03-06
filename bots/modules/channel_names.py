# -*- coding: utf-8 -*-
import os
from csv import reader as CSVReader, writer as CSVWriter
from time import time as time_now
from random import random
from datetime import datetime
from difflib import get_close_matches

from bot_utils.shared import BOT_CHANNEL_CATEGORY, KOISHI_PATH, DUNGEON, STAFF_ROLE

from hata import Lock, KOKORO, alchemy_incendiary, Task, eventlist, Embed, DiscordException, ERROR_CODES, BUILTIN_EMOJIS
from hata.ext.commands import checks, Command, Pagination, Closer, wait_for_reaction

FILE_NAME = 'channel_names.csv'

FILE_PATH = os.path.join(KOISHI_PATH, 'bots', 'modules', FILE_NAME)
FILE_LOCK = Lock(KOKORO)
EDIT_LOCK = Lock(KOKORO)

DEFAULT_NAME = 'gogo-maniac'

DAY = 24.0 * 60.0 * 60.0
DAY_CHANCE_MULTIPLINER = 0.01 / DAY

SPACE_CHAR = '-'

CHANNEL_CHAR_TABLE = {}
for source, target in (
        ('!', 'ǃ'),
        ('?', '？'),
            ):
    CHANNEL_CHAR_TABLE[source] = target
    CHANNEL_CHAR_TABLE[target] = target

# Add quote chars
for char in ('\'', '`', '"'):
    CHANNEL_CHAR_TABLE[char] = '’'

# Add space chars
for char in (' ', '-', '\t', '\n', '~'):
    CHANNEL_CHAR_TABLE[char] = SPACE_CHAR

# Add lowercase letters
for char in range(b'a'[0], b'z'[0]+1):
    char = chr(char)
    CHANNEL_CHAR_TABLE[char] = char

# Add uppercase letters
for shift in range(0, b'Z'[0]-b'A'[0]+1):
    source = chr(b'A'[0] + shift)
    target = chr(ord('𝖠') + shift)
    CHANNEL_CHAR_TABLE[source] = target
    CHANNEL_CHAR_TABLE[target] = target

# Add numbers
for char in range(b'0'[0], b'9'[0]+1):
    char = chr(char)
    CHANNEL_CHAR_TABLE[char] = char

# Cleanup
del shift, target, source, char


def escape_name(name):
    created = []
    last = SPACE_CHAR
    for char in name:
        char = CHANNEL_CHAR_TABLE.get(char)
        if char is None:
            continue
        
        if char == SPACE_CHAR and last == SPACE_CHAR:
            continue
        
        created.append(char)
        last = char
    
    if created and created[-1] == SPACE_CHAR:
        del created[-1]
    
    return ''.join(created)


class ChannelNameDescriber(object):
    __slots__ = ('_chance', 'last_present', 'name', 'weight')
    
    @classmethod
    def from_csv_line(cls, line):
        name, last_present, weight = line
        
        last_present = int(last_present, base=16)
        weight = int(weight, base=16)
        
        self = object.__new__(cls)
        
        self.name = name
        self.last_present = last_present
        self.weight = weight
        self._chance = None
        
        return self
    
    @classmethod
    def from_name_and_weight(cls, name, weight):
        self = object.__new__(cls)
        
        self.name = name
        self.last_present = int(time_now())
        self.weight = weight
        self._chance = None
        
        return self
    
    @property
    def chance(self):
        chance = self._chance
        if chance is None:
            self._chance = chance = (1.0 + (time_now()-self.last_present)*DAY_CHANCE_MULTIPLINER) * self.weight
        
        return chance
    
    def __len__(self):
        return 3
    
    def __iter__(self):
        yield self.name
        yield self.last_present.__format__('X')
        yield self.weight.__format__('X')
    
    def present(self):
        self.last_present = int(time_now())
        self._chance = 0.0


async def get_random_names(count):
    names = await read_channels()
    choosed = []
    if len(names) <= count:
        for describer in names:
            choosed.append(describer.name)
            describer.present()
        
        for _ in range(len(names), count):
            choosed.append(DEFAULT_NAME)
    
    else:
        total_chance = 0.0
        for describer in names:
            total_chance += describer.chance
        
        for _ in range(count):
            position = total_chance*random()
            
            # Add some extra for security issues. If the first name was selected and `random()` returns `0.0`, then
            # the same name could be selected twice.
            if position == 0.0:
                position = 0.01
            
            for describer in names:
                chance = describer.chance
                position -= chance
                if position > 0.0:
                    continue
                
                total_chance -= chance
                describer.present()
                choosed.append(describer.name)
                break
    
    await write_channels(names)
    return choosed


def read_channels_task():
    names = []
    if not os.path.exists(FILE_PATH):
        return names
    
    with open(FILE_PATH, 'r') as file:
        reader = CSVReader(file)
        for line in reader:
            describer = ChannelNameDescriber.from_csv_line(line)
            names.append(describer)
    
    return names


def write_channels_task(names):
    with open(FILE_PATH, 'w') as file:
        writer = CSVWriter(file)
        writer.writerows(names)


async def read_channels():
    async with FILE_LOCK:
        return await KOKORO.run_in_executor(read_channels_task)


async def write_channels(names):
    async with FILE_LOCK:
        await KOKORO.run_in_executor(alchemy_incendiary(write_channels_task, (names,)))


async def do_rename():
    async with EDIT_LOCK:
        if not BOT_CHANNEL_CATEGORY.guild.permissions_for(Koishi).can_manage_channel:
            return
        
        channels = BOT_CHANNEL_CATEGORY.channel_list
        count = len(channels)
        if not count:
            return
        
        names = await get_random_names(count)
        
        for channel, name in zip(channels, names):
            await Koishi.channel_edit(channel, name=name)


def cycle_rename():
    module_locals.handle = KOKORO.call_later(DAY, cycle_rename)
    Task(do_rename(), KOKORO)

# Use class to store changeable global variables since module globals might not be collected.
class module_locals:
    # schedule renaming
    handle = None



CHANNEL_NAME_COMMANDS = eventlist(type_=Command)

def setup(lib):
    category = Koishi.command_processer.get_category('CHANNEL NAMES')
    if (category is None):
        Koishi.command_processer.create_category('CHANNEL NAMES', checks=[checks.has_role(STAFF_ROLE)])
    
    Koishi.commands.extend(CHANNEL_NAME_COMMANDS)

    module_locals.handle = KOKORO.call_at(
        datetime.utcnow().replace(microsecond=0, second=0, minute=0, hour=0).timestamp()+DAY, do_rename)

def teardown(lib):
    Koishi.commands.unextend(CHANNEL_NAME_COMMANDS)
    
    handle = module_locals.handle
    if (handle is not None):
        module_locals.handle = None
        handle.cancel()


@CHANNEL_NAME_COMMANDS(category='CHANNEL NAMES')
async def list_bot_channel_names(client, message):
    """
    Lists the already added bot channel names.
    """
    names = await read_channels()
    
    descriptions = []
    if names:
        lines = []
        page_size = 0
        for index, describer in enumerate(names, 1):
            if page_size == 16:
                description = '\n'.join(lines)
                descriptions.append(description)
                lines.clear()
                page_size = 0
            else:
                page_size += 1
                line = f'{index}. [{describer.weight}] {describer.name}'
                lines.append(line)
        
        if page_size:
            description = '\n'.join(lines)
            descriptions.append(description)
            lines.clear()
    else:
        descriptions.append('*none*')
    
    pages = [Embed('Bot channel names', description) for description in descriptions]
    await Pagination(client, message.channel, pages)


def check_staff_role(event):
    return event.user.has_role(STAFF_ROLE)

ADD_EMOJI_OK     = BUILTIN_EMOJIS['ok_hand']
ADD_EMOJI_CANCEL = BUILTIN_EMOJIS['x']
ADD_EMOJI_EMOJIS = (ADD_EMOJI_OK, ADD_EMOJI_CANCEL)

@CHANNEL_NAME_COMMANDS( category='CHANNEL NAMES', separator='|')
async def add_bot_channel_name(client, message, weight:int, name):
    """
    Adds the given channel name to the bot channel names.
    
    When adding a command please also define weight and not only name as: `weight | name`
    """
    if EDIT_LOCK.locked():
        await Closer(client, message.channel, Embed('Ohoho', 'A bot channel editing is already taking place.'))
        return
    
    async with EDIT_LOCK:
        name = escape_name(name)
        if not 2 <= len(name) <= 100:
            await Closer(client, message.channell, Embed(f'Too long or short name', name))
            return
        
        names = await read_channels()
        close_matches = get_close_matches(name, [describer.name for describer in names], n=1, cutoff=0.8)
        if not close_matches:
            overwrite = False
            embed = Embed('Add bot channel name',
                f'Would you like to add a channel name:\n{name}\nWith weight of {weight}.')
        elif close_matches[0] == name:
            overwrite = True
            embed = Embed('Add bot channel name',
                f'Would you like to overwrite the following bot channel name:\n'
                f'{name}\n'
                f'To weight of {weight}.')
        else:
            overwrite = False
            embed = Embed('Add bot channel name',
                f'There is a familiar channel name already added: {close_matches[0]}\n'
                f'Would you like to overwrite the following bot channel name:\n'
                f'{name}\n'
                f'To weight of {weight}.')
        
        message = await client.message_create(message.channel, embed=embed)
        for emoji_ in ADD_EMOJI_EMOJIS:
            await client.reaction_add(message, emoji_)
        
        try:
            event = await wait_for_reaction(client, message, check_staff_role, 300.)
        except TimeoutError:
            emoji_ = ADD_EMOJI_CANCEL
        else:
            emoji_ = event.emoji
        
        if message.channel.cached_permissions_for(client).can_manage_messages:
            try:
                await client.reaction_clear(message)
            except BaseException as err:
                if isinstance(err, ConnectionError):
                    # no internet
                    return
                
                if isinstance(err, DiscordException):
                    if err.code in (
                            ERROR_CODES.invalid_access, # client removed
                            ERROR_CODES.unknown_message, # message deleted
                            ERROR_CODES.invalid_permissions, # permissions changed meanwhile
                                ):
                        return
                
                raise
        
        if emoji_ is ADD_EMOJI_OK:
            if overwrite:
                for describer in names:
                    if describer.name == describer:
                        describer.weight = weight
                
                footer = 'Name overwritten succesfully.'
            else:
                describer = ChannelNameDescriber.from_name_and_weight(name, weight)
                names.append(describer)
                footer = 'Name added succesfully.'
            await write_channels(names)
        
        elif emoji_ is ADD_EMOJI_CANCEL:
            footer = 'Name adding cancelled.'
        
        else: # should not happen
            return
        
        embed.add_footer(footer)
        
        await client.message_edit(message, embed=embed)


@CHANNEL_NAME_COMMANDS(category='CHANNEL NAMES')
async def do_bot_channel_rename(client, message):
    """
    Adds the given channel name to the bot channel names.
    
    When adding a command please also define weight and not only name as: `weight | name`
    """
    await do_rename()
    await Closer(client, message.channel, Embed(description='Rename done'))
