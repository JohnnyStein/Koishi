# -*- coding: utf-8 -*-
import os, sys, subprocess, re
from pathlib import Path
from subprocess import TimeoutExpired
from hata import eventlist, Color, KOKORO, Embed, ScarletLock, sleep, Guild
from hata.ext.commands import Command, checks
from bot_utils.interpreter import parse_code_content
from bot_utils.shared import DUNGEON, KOISHI_PATH

# installing nsjail:
# make a folder for it somewhere
# $ sudo apt install autoconf bison flex gcc g++ git libprotobuf-dev libtool make pkg-config protobuf-compiler
# $ sudo apt-get install libnl-route-3-dev
# $ git clone https://github.com/google/nsjail.git
# $ cd nsjail && git checkout 3.0 # <- verison number
# $ make
# $ sudo cp ".../nsjail/nsjail" "/usr/sbin/" # Copy it.

SNEKBOX_COLOR = Color.from_rgb(255, 16, 124)
SNEKBOX_COMMANDS = eventlist(type_=Command, category='SNEKBOX')

CGROUP_PIDS_PARENT = Path('/sys/fs/cgroup/pids/NSJAIL')
CGROUP_MEMORY_PARENT = Path('/sys/fs/cgroup/memory/NSJAIL')

MEM_MAX = 52428800
MAX_TIMEOUT = 13

NSJAIL_EXECUTABLE = os.getenv('NSJAIL_PATH', '/usr/sbin/nsjail')
NSJAIL_CONFIG = os.getenv('NSJAIL_CFG', os.path.join(KOISHI_PATH, 'bots', 'modules', 'nsjail.cfg'))

PYTHON_EXECUTABLE = '/usr/bin/python3.8'
SNEKBOXING_PATH = Path('/snekbox')

IS_UNIX = (sys.platform != 'win32')

LOG_RP = re.compile('\[[IDWEF]\]\[.+?\] (.*)')

EVAL_LOCK = ScarletLock(KOKORO, 2)

def setup(lib):
    if IS_UNIX:
        CGROUP_PIDS_PARENT.mkdir(parents=True, exist_ok=True)
        CGROUP_MEMORY_PARENT.mkdir(parents=True, exist_ok=True)
        SNEKBOXING_PATH.mkdir(parents=True, exist_ok=True)
        
        try:
            (CGROUP_MEMORY_PARENT / 'memory.limit_in_bytes').write_text(str(MEM_MAX), encoding='utf-8')
        except PermissionError:
            pass
        else:
            try:
                (CGROUP_MEMORY_PARENT / 'memory.memsw.limit_in_bytes').write_text(str(MEM_MAX), encoding='utf-8')
            except PermissionError:
                # sys.stderr.write(f'From {__file__}: Failed to setup memory swap limit\n')
                pass
    
    main_client.command_processer.create_category('SNEKBOX', checks=[checks.is_guild(DUNGEON)])
    main_client.commands.extend(SNEKBOX_COMMANDS)

def teardown(lib):
    main_client.command_processer.delete_category('SNEKBOX')

def build_output(output, returncode):
    lines = output.decode('utf-8').splitlines()
    index = 0
    limit = len(lines)
    while True:
        if index == limit:
            lines = []
            break
        
        line = lines[index]
        index +=1
        
        parsed = LOG_RP.fullmatch(line)
        if parsed is None:
            continue
        
        if parsed.group(1).startswith('Executing'):
            lines = lines[index:-(1+(returncode == 137))]
            break
    
    if not lines:
        return '[NO OUTPUT]'
    
    if len(lines) > 40:
        del lines[40:]
        is_truncated = True
    else:
        is_truncated = False
    
    content_left_length = 2000
    
    index = 0
    limit = len(lines)
    while True:
        if index == limit:
            break
        
        line = lines[index]
        index +=1
        line_length = len(line)
        
        content_left_length -= line_length
        if content_left_length < 0:
            lines[index-1] = line[:line_length-content_left_length]
            del lines[index:]
            is_truncated = True
            break
    
    
    if is_truncated:
        lines.append('[OUTPUT TRUNCATED]')
    
    return '\n'.join(lines)

ACTIVE_EXECUTORS = set()

class EvalUserLock(object):
    __slots__ = ('channel', 'client', 'process', 'user_id',)
    def __new__(cls, user_id):
        self = object.__new__(cls)
        self.user_id = user_id
        self.channel = None
        self.client = None
        self.process = None
        return self
    
    def __enter__(self):
        ACTIVE_EXECUTORS.add(self.user_id)
        return self
    
    def register_input_source(self, client, channel, process):
        self.client = client
        self.channel = channel
        self.process = process
        
        client.command_processer.append(channel, self)
    
    async def __call__(self, client, message):
        if message.author.id != self.user_id:
            return
        
        stdin = self.process.stdin
        if stdin.is_closing():
            return
        
        stdin.write(message.content.encode())
        stdin.write(b'\n')
        await stdin.drain()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            ACTIVE_EXECUTORS.remove(self.user_id)
        except KeyError:
            pass
        
        self.client.command_processer.remove(self.channel, self)

if IS_UNIX:
    async def eval_description(client,message):
        prefix = client.command_processer.get_prefix_for(message)
        return Embed('eval', (
            'Executes the given code in an isolated environment.\n'
            'Usages:\n'
            f'{prefix}eval # code goes here\n'
            '# code goes here\n'
            '# code goes here\n'
            '\n'
            f'{prefix}eval\n'
            '```\n'
            '# code goes here\n'
            '# code goes here\n'
            '```\n'
            '*not code*\n'
            '\n'
            '... and many more ways.'
                ), color=SNEKBOX_COLOR).add_footer(
                f'{DUNGEON} only!')
     
    @SNEKBOX_COMMANDS(name='eval', aliases=['e'], description=eval_description)
    async def eval_(client, message, content):
        code, is_exception = parse_code_content(content)
        if is_exception and (code is None):
            await eval_description(client, message)
            return
        
        user_id = message.author.id
        if user_id in ACTIVE_EXECUTORS:
            await client.message_create(message.channel,
                embed=Embed('You have an eval job queued up', 'Please be patient.', color=SNEKBOX_COLOR))
            return
        
        if is_exception:
            await client.message_create(message.channel, embed=Embed('Parsing error', code, color=SNEKBOX_COLOR))
            return
        
        with client.keep_typing(message.channel), EvalUserLock(user_id) as user_lock:
            async with EVAL_LOCK:
                process = await KOKORO.subprocess_exec(NSJAIL_EXECUTABLE, [
                        '--config', NSJAIL_CONFIG,
                        f'--cgroup_mem_max={MEM_MAX}',
                        '--cgroup_mem_mount', str(CGROUP_MEMORY_PARENT.parent),
                        '--cgroup_mem_parent', CGROUP_MEMORY_PARENT.name,
                        '--cgroup_pids_max=1',
                        '--cgroup_pids_mount', str(CGROUP_PIDS_PARENT.parent),
                        '--cgroup_pids_parent', CGROUP_PIDS_PARENT.name,
                        '--',
                        PYTHON_EXECUTABLE, '-Iqu', '-c', code
                            ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                        )
                
                user_lock.register_input_source(client, message.channel, process)
                
                try:
                    await process.wait(timeout=MAX_TIMEOUT)
                except TimeoutExpired:
                    await process.kill()
                
                returncode = process.returncode
                if returncode is None or returncode == 255:
                    title = f'Your eval job has failed! Returncode: {returncode!r}'
                    description = 'A fatal NsJail error occurred'
                else:
                    if returncode == 137:
                        title = f'Your eval job timed out or ran out of memory. Returncode: {returncode!r}'
                    else:
                        title = f'Your eval job has completed with return code {returncode}.'
                    
                    output = await process.stdout.read()
                    description = build_output(output, returncode)
                
                author = message.author
                await client.message_create(message.channel,
                    embed=Embed(title, description, color=SNEKBOX_COLOR).add_author(author.avatar_url, author.full_name),
                    allowed_mentions=None)
