import os, re
join=os.path.join
from collections import deque
from threading import current_thread
from time import perf_counter, time as time_now, monotonic
from io import StringIO

from hata.dereaddons_local import multidict_titled, titledstr, _spaceholder,\
    alchemy_incendiary
from hata.futures import Future,sleep,Task, WaitTillAll, render_exc_to_list,\
    CancelledError, _EXCFrameType, render_frames_to_list
from hata.parsers import eventlist
from hata.client_core import CLIENTS
from hata.eventloop import EventThread
from hata.py_hdrs import DATE, METH_PATCH, METH_GET, METH_DELETE, METH_POST,\
    METH_PUT, AUTHORIZATION, CONTENT_TYPE

from hata.py_reqrep import Request_CM
from hata.exceptions import DiscordException
from hata.others import to_json,from_json,quote
from hata.emoji import BUILTIN_EMOJIS
from hata.message import Message
from hata.others import ext_from_base64, bytes_to_base64, VoiceRegion,      \
    VerificationLevel, MessageNotificationLevel, ContentFilterLevel,        \
    DISCORD_EPOCH, Discord_hdrs
from hata.user import User
from hata.role import Role
from hata.client import Client, Achievement
from hata.oauth2 import UserOA2, parse_oauth2_redirect_url
from hata.channel import cr_pg_channel_object, ChannelCategory, ChannelText,\
    ChannelGuildBase
from hata.guild import PartialGuild
from hata.http import VALID_ICON_FORMATS, VALID_ICON_FORMATS_EXTENDED
from hata.integration import Integration
from email._parseaddr import _parsedate_tz
from datetime import datetime,timedelta,timezone
from hata.embed import Embed
from hata.webhook import Webhook
from hata.ios import ReuAsyncIO, AsyncIO
from hata.events import wait_for_message, Pagination, wait_for_reaction

RATELIMIT_RESET=Discord_hdrs.RATELIMIT_RESET
RATELIMIT_RESET_AFTER=Discord_hdrs.RATELIMIT_RESET_AFTER

ratelimit_commands=eventlist()

def entry(client):
    client.events.message_create.shortcut.extend(ratelimit_commands)
    
def exit(client):
    client.events.message_create.shortcut.unextend(ratelimit_commands)


##UNLIMITED  :
##    reaction_users
##    message_logs
##    message_get
##    download_attachment
##    invite_get_channel
##    permission_ow_create
##    permission_ow_delete
##    channel_edit
##    channel_delete
##    oauth2_token
##    webhook_create
##    webhook_get_channel
##    guild_create
##    guild_get
##    guild_delete
##    guild_edit
##    audit_logs
##    guild_bans
##    guild_ban_add
##    guild_ban_delete
##    guild_ban_get
##    channel_move
##    channel_create
##    guild_embed_get
##    guild_embed_edit
##    guild_emojis
##    emoji_get
##    integration_get_all
##    invite_get_guild
##    guild_prune
##    guild_prune_estimate
##    role_create
##    role_move
##    role_edit
##    role_delete
##    webhook_get_guild
##    invite_delete
##    client_application_info
##    user_info
##    client_user
##    channel_private_get_all
##    channel_private_create
##    guild_delete
##    webhook_get
##    webhook_edit
##    webhook_delete
##    webhook_get_token
##    webhook_edit_token
##    webhook_delete_token
##    guild_regions
##    guild_channels
##    guild_roles
##    guild_widget_get
##    channel_follow
##    
##group       : reaction
##limit       : 1
##reset       : 0.25s
##limited by  : channel
##members     :
##    reaction_add
##    reaction_delete
##    reaction_delete_own
##    reaction_clear
##
##group       : message_create
##limit       : 5
##reset       : 4s
##limited by  : channel
##members     :
##    message_create
##    
##    
##group       : message_delete_multiple
##limit       : 1
##reset       : 3s
##limited by  : channel
##members     :
##    message_delete_multiple
##
##group       : message_edit
##limit       : 5
##reset       : 4s
##limited by  : channel
##members     :
##    message_edit
##
##group       : pinning
##limit       : 5
##reset       : 4s
##limited by  : channel
##members     :
##    message_pin
##    message_unpin
##
##group       : pinneds
##limit       : 1
##reset       : 5s
##limited by  : global
##members     :
##    message_pinneds
##
##
##group       : typing
##limit       : 5
##reset:      : 5s
##limited by  : channel
##members     :
##    typing
##
##group       : invite_create
##limit       : 5
##reset       : 15s
##limited by  : global
##members     :
##    invite_create
##
##group       : client_gateway_bot
##limit       : 2
##reset       : 5s
##limited by  : global
##members     :
##    client_gateway_bot
##
##group       : emoji_create
##limit       : 50
##reset       : 3600s
##limited by  : guild
##members     :
##    emoji_create
##
##group       : emoji_delete
##limit       : 1
##reset       : 3s
##limited by  : global
##members     :
##    emoji_delete
##
##group       : emoji_edit
##limit       : 1
##reset       : 3s
##limited by  : global
##members     :
##    emoji_edit
##
##group       : client_edit_nick
##limit       : 1
##reset       : 2s
##limited by  : global
##members     :
##    client_edit_nick
##
##group       : guild_user_delete
##limit       : 5
##reset       : 2s
##limited by  : guild
##members     :
##    guild_user_delete
##
##group       : user_edit
##limit       : 10
##reset       : 10s
##limited by  : guild
##members     :
##    user_edit
##
##group       : guild_user_add
##limit       : 10
##reset       : 10s
##limited by  : guild
##members     :
##    guild_user_add
##
##group       : user_role
##limit       : 10
##reset       : 10s
##limited by  : guild
##members     :
##    user_role_add
##    user_role_delete
##
##group       : invite_get
##limit       : 250
##reset       : 6s
##limited by  : global
##members     :
##    invite_get
##
##group       : client_edit
##limit       : 2
##reset       : 3600s
##limited by  : global
##members     :
##    client_edit
##
##group       : user_guilds
##limit       : 1
##reset       : 1s
##limited by  : global
##members     :
##    user_guilds
##
##group       : guild_get_all
##limit       : 1
##reset       : 1s
##limited by  : global
##members     :
##    guild_get_all
##    
##group       : user_get
##limit       : 30
##reset       : 30s
##limited by  : global
##members     :
##    user_get
##
##group       : webhook_execute
##limit       : 5
##reset       : 2s
##limited by  : webhook
##members     :
##    webhook_execute
##
##group       : guild_users
##limit       : 10
##reset       : 10s
##limited by  : webhook
##members     :
##    guild_users
##    
##group       : guild_user_get
##limit       : 5
##reset       : 2s
##limited by  : global
##members:
##    guild_user_get
##
##group       : message_delete 
##case 1      : newer than 2 week
##    limit   : UNLIMITED
##case 2      : older than 2 week, own
##    limit   : 3
##    reset   : 1s
##case 3      : older than 2 week, other's
##    limit   : 30
##    reset   : 120s
##members     :
##    message_delete
##
##group       : message_suppress_embeds
##limit       : 3
##reset       : 1
##limited by  : global
##members:
##    message_suppress_embeds
##
##group       : achievement_get
##limit       : 5
##reset       : 5
##limited by  : global
##members:
##    achievement_get
##
##group       : achievement_create
##limit       : 5
##reset       : 5
##limited by  : global
##members:
##    achievement_create
##
##group       : achievement_delete
##limit       : 5
##reset       : 5
##limited by  : global
##members:
##    achievement_delete
##
##group       : achievement_get_all
##limit       : 5
##reset       : 5
##limited by  : global
##members:
##    achievement_get_all
##
##group       : user_achievement_update
##limit       : 5
##reset       : 5
##limited by  : global
##members:
##    user_achievement_update


def parsedate_to_datetime(data):
    *dtuple, tz = _parsedate_tz(data)
    if tz is None:
        return datetime(*dtuple[:6])
    return datetime(*dtuple[:6],tzinfo=timezone(timedelta(seconds=tz)))

def parse_header_ratelimit(headers):
    delay1=( \
        datetime.fromtimestamp(float(headers[RATELIMIT_RESET]),timezone.utc)
        -parsedate_to_datetime(headers[DATE])
            ).total_seconds()
    delay2=float(headers[RATELIMIT_RESET_AFTER])
    return (delay1 if delay1<delay2 else delay2)

async def bypass_request(client,method,url,data=None,params=None,reason=None,header=None,decode=True,):
    self=client.http
    if header is None:
        header=self.header.copy()
    header[titledstr.bypass_titling('X-RateLimit-Precision')]='millisecond'
    
    if CONTENT_TYPE not in header and data and isinstance(data,(dict,list)):
        header[CONTENT_TYPE]='application/json'
        #converting data to json
        data=to_json(data)

    if reason:
        header['X-Audit-Log-Reason']=quote(reason)
    
    try_again=5
    while try_again:
        try_again-=1
        with RLTPrinterBuffer() as buffer:
            buffer.write(f'Request started : {url} {method}\n')
            
        try:
            async with Request_CM(self._request(method,url,header,data,params)) as response:
                if decode:
                    response_data = await response.text(encoding='utf-8')
                else:
                    response_data=''
        except OSError as err:
            #os cant handle more, need to wait for the blocking job to be done
            await sleep(0.1,self.loop)
            #invalid adress causes OSError too, but we will let it run 5 times, then raise a ConnectionError
            continue
        
        with RLTPrinterBuffer() as buffer:
            headers=response.headers
            status=response.status
            if headers['content-type']=='application/json':
                response_data=from_json(response_data)
            
            value=headers.get('X-Ratelimit-Global',None)
            if value is not None:
                buffer.write(f'global : {value}\n')
            value=headers.get('X-Ratelimit-Limit',None)
            if value is not None:
                buffer.write(f'limit : {value}\n')
            value=headers.get('X-Ratelimit-Remaining',None)
            if value is not None:
                buffer.write(f'remaining : {value}\n')
                
            value=headers.get('X-Ratelimit-Reset',None)
            if value is not None:
                delay=parse_header_ratelimit(headers)
                buffer.write(f'reset : {value}, after {delay} seconds\n')
            value=headers.get('X-Ratelimit-Reset-After',None)
            if value is not None:
                buffer.write(f'reset after : {value}\n')
    
            
            if 199<status<305:
                if headers.get('X-Ratelimit-Remaining','1')=='0':
                    buffer.write(f'reached 0\n try again after {delay}\n',)
                return response_data
            
            if status==429:
                retry_after=response_data['retry_after']/1000.
                buffer.write(f'RATE LIMITED\nretry after : {retry_after}\n',)
                await sleep(retry_after,self.loop)
                continue
            
            elif status==500 or status==502:
                await sleep(10./try_again+1.,self.loop)
                continue
            
            raise DiscordException(response,response_data)

    try:
        raise DiscordException(response,response_data)
    except UnboundLocalError:
        raise ConnectionError('Invalid adress')

class RLTCTX(object): #rate limit tester context manager
    active_ctx=None
    
    __slots__ = ('task', 'client', 'channel', 'title',)
    
    def __new__(cls,client,channel,title):
        thread=current_thread()
        if type(thread) is not EventThread:
            raise RuntimeError(f'{cls.__name__} can be created only at an {EventThread.__name__}')
        current_task=thread.current_task
        if current_task is None:
            raise RuntimeError(f'{cls.__name__} was created outside of a task')
            
        self=object.__new__(cls)
        self.task=current_task
        self.client=client
        self.channel=channel
        self.title=title
        return self

    def __enter__(self):
        active_ctx=type(self).active_ctx
        if (active_ctx is not None):
            raise RuntimeError(f'There is an already active {self.__class__.__name__} right now.')
        
        type(self).active_ctx=self
        return self
    
    def __exit__(self,exc_type,exc_val,exc_tb):
        type(self).active_ctx=None
        if exc_type is CancelledError:
            return True
        
        if exc_type is None:
            Task(self._render_exit_result(),self.client.loop)
            return True
        
        Task(self._render_exit_exc(exc_val,exc_tb),self.client.loop)
        return True
    
    async def _render_exit_result(self):
        unit_result = []
        
        for unit in RLTPrinterBuffer.buffers:
            if type(unit) is str:
                unit_result.append(unit)
                unit_result.append('\n')
                continue
            
            task=unit.task
            unit_result.append(f'Task `{task.name}`')
            unit_result.append('\n')
            
            for date,buffer in unit.buffer:
                date=date.__format__('%Y.%m.%d-%H:%M:%S-%f')
                unit_result.append(date)
                unit_result.append(':\n')
                
                unit_result.extend(buffer)
                unit_result.append('\n')
                
            exception=task.exception()
            if exception is None:
                continue
            
            if type(exception) is DiscordException:
                unit_result.append(repr(exception))
                unit_result.append('\n')
                continue
            
            unit_result.append('```')
            await self.client.loop.run_in_executor(alchemy_incendiary(render_exc_to_list,(exception,unit_result,),))
            unit_result.append('\n')
            unit_result.append('```')
            unit_result.append('\n')

        RLTPrinterBuffer.buffers.clear()
        
        pages = []
        contents = []
        page_content_length = 0
        in_code_block=0
        
        for str_ in unit_result:
            local_length=len(str_)
            
            page_content_length+=local_length
            if page_content_length<1996:
                if str_=='```':
                    in_code_block^=1
                contents.append(str_)
                continue
            
            if contents[-1]=='\n':
                del contents[-1]
            
            if in_code_block:
                if contents[-1]=='```':
                    del contents[-1]
                else:
                    if str_=='```':
                        in_code_block=0
                    contents.append('\n```')
            else:
                if str_=='```':
                    in_code_block=2
            
            pages.append(Embed(self.title,''.join(contents)))
            contents.clear()
            if in_code_block==1:
                contents.append('```\n')
                local_length+=4
            elif in_code_block==2:
                contents.append('```')
                local_length+=3
                in_code_block=1
            
            if str_=='\n':
                page_content_length=0
                continue
            
            contents.append(str_)
            page_content_length=local_length
            continue

        if page_content_length:
            pages.append(Embed(self.title,''.join(contents)))
            
        del unit_result
        del contents
        
        if pages:
            page_count=len(pages)
            index=0
            for page in pages:
                index=index+1
                page.add_footer(f'Page {index}/{page_count}')
        else:
            pages.append(Embed(self.title,).add_footer('Page 1/1'))
        
        await Pagination(self.client,self.channel,pages)
        
    async def _render_exit_exc(self,exception,tb):
        frames=[]
        while True:
            if tb is None:
                break
            frame=_EXCFrameType(tb)
            frames.append(frame)
            tb=tb.tb_next
        
        extend=[]
        extend.append('```Traceback (most recent call last):\n')
        await self.client.loop.run_in_executor(alchemy_incendiary(render_frames_to_list,(frames,),{'extend':extend}))
        extend.append(repr(exception))
        extend.append('\n```')
        pages = []
        contents = []
        page_content_length = 0
    
        for str_ in extend:
            local_length=len(str_)
            page_content_length+=local_length
            if page_content_length<1996:
                contents.append(str_)
                continue
                
            if contents[-1]=='\n':
                del contents[-1]
            
            contents.append('\n```')
            pages.append(Embed(self.title,''.join(contents)))
            contents.clear()
            contents.append('```\n')
            
            if str_=='\n':
                page_content_length=0
                continue
            
            contents.append(str_)
            page_content_length=local_length
            continue

        if page_content_length:
            pages.append(Embed(self.title,''.join(contents)))
            
        del contents
        
        page_count=len(pages)
        index=0
        for page in pages:
            index=index+1
            page.add_footer(f'Page {index}/{page_count}')
        
        await Pagination(self.client,self.channel,pages)
    
    def write(self,content):
        RLTPrinterBuffer.buffers.append(content)
    
    async def send(self,description):
        await Pagination(self.client,self.channel,[Embed(self.title,description).add_footer('Page 1/1')])
        raise CancelledError()
            
class RLTPrinterUnit(object):
    __slots__=('task','buffer','start_new_block',)
    def __init__(self,task):
        self.task=task
        self.buffer=[]
        self.start_new_block=True
    
    def write(self,content):
        if self.start_new_block:
            buffer=[]
            self.buffer.append((datetime.now(),buffer),)
            self.start_new_block=False
        else:
            buffer=self.buffer[-1][1]
        
        buffer.append(content)
    
class RLTPrinterBuffer(object):
    buffers=[]
    __slots__=('buffer',)
    
    def __init__(self):
        thread=current_thread()
        if type(thread) is not EventThread:
            raise RuntimeError(f'{self.__name__}.__enter__ can be used only at an {EventThread.__name__}')
        current_task=thread.current_task
        if current_task is None:
            raise RuntimeError(f'{self.__name__}.__enter__ was used outside of a task')
        
        for buffer in self.buffers:
            if type(buffer) is str:
                continue
            if buffer.task is current_task:
                buffer.start_new_block=True
                break
        else:
            buffer=RLTPrinterUnit(current_task)
            self.buffers.append(buffer)
        
        self.buffer=buffer
    
    def __enter__(self):
        return self.buffer
    
    def __exit__(self,exc_type,exc_val,exc_tb):
        self.buffer.start_new_block=True
        return False
        
        
async def reaction_add(client,message,emoji,):
    channel_id=message.channel.id
    message_id=message.id
    reaction=emoji.as_reaction
    return await bypass_request(client,METH_PUT,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/{message_id}/reactions/{reaction}/@me',
        )
        
async def reaction_delete(client,message,emoji,user,):
    channel_id=message.channel.id
    message_id=message.id
    reaction=emoji.as_reaction
    user_id=user.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/{message_id}/reactions/{reaction}/{user_id}',
        )

async def reaction_delete_own(client,message,emoji,):
    channel_id=message.channel.id
    message_id=message.id
    reaction=emoji.as_reaction
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/{message_id}/reactions/{reaction}/@me',
        )

async def reaction_clear(client,message,):
    channel_id=message.channel.id
    message_id=message.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/{message_id}/reactions',)

async def reaction_users(client,message,emoji,):
    if message.reactions is None:
        return []
    channel_id=message.channel.id
    message_id=message.id
    reaction=emoji.as_reaction
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/{message_id}/reactions/{reaction}',
        params={'limit':100},)

async def message_create(client,channel,content=None,embed=None,):
    data={}
    if content is not None and content:
        data['content']=content
    if embed is not None:
        data['embed']=embed.to_data()
    channel_id=channel.id
    data = await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages',
        data,)
    return Message.new(data,channel)

async def message_delete(client,message,):
    channel_id=message.channel.id
    message_id=message.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/{message_id}',)

async def message_delete_multiple(client,messages,):
    if len(messages)==0:
        return
    if len(messages)==1:
        return message_delete(client,messages[0])
    data={'messages':[message.id for message in messages]}
    channel_id=messages[0].channel.id
    return await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/bulk_delete',
        data,)

async def message_edit(client,message,content=None,embed=None,):
    data={}
    if content is not None:
        data['content']=content
    if embed is not None:
        data['embed']=embed.to_data()
    channel_id=message.channel.id
    message_id=message.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/{message_id}',
        data,)

async def message_pin(client,message,):
    channel_id=message.channel.id
    message_id=message.id
    return await bypass_request(client,METH_PUT,
        f'https://discordapp.com/api/v7/channels/{channel_id}/pins/{message_id}',
        )

async def message_unpin(client,message,):
    channel_id=message.channel.id
    message_id=message.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/channels/{channel_id}/pins/{message_id}',
        )

async def message_pinneds(client,channel,):
    channel_id=channel.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/channels/{channel_id}/pins',
        )

async def message_logs(client,channel,):
    channel_id=channel.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages',
        params={'limit':1},)

async def message_get(client,channel,message_id,):
    channel_id=channel.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/{message_id}',
        )

async def download_attachment(client,attachment,):
    if attachment.proxy_url.startswith('https://cdn.discordapp.com/'):
        url=attachment.proxy_url
    else:
        url=attachment.url
    return await bypass_request(client,METH_GET,url,header=multidict_titled(),decode=False,
        )


async def typing(client,channel,):
    channel_id=channel.id
    return await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/channels/{channel_id}/typing',
        )

async def client_edit(client,name='',avatar=b'',):
    data={}
    if name:
        if not (1<len(name)<33):
            raise ValueError(f'The length of the name can be between 2-32, got {len(name)}')
        data['username']=name
    
    if avatar is None:
        data['avatar']=None
    elif avatar:
        avatar_data=bytes_to_base64(avatar)
        ext=ext_from_base64(avatar_data)
    return await bypass_request(client,METH_PATCH,
        'https://discordapp.com/api/v7/users/@me',
        data,)

async def client_connections(client,):
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/users/@me/connections',
        )

async def client_edit_nick(client,guild,nick,):
    guild_id=guild.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/members/@me/nick',
        {'nick':nick},)

async def client_gateway_bot(client,):
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/gateway/bot',
        )

async def client_application_info(client,):
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/oauth2/applications/@me',
        )

async def client_login_static(client,):
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/users/@me',
        )

async def client_logout(client,):
    return await bypass_request(client,METH_POST,
        'https://discordapp.com/api/v7/auth/logout',
        )


async def permission_ow_create(client,channel,target,allow,deny,):
    if type(target) is Role:
        type_='role'
    elif type(target) in (User,Client,UserOA2):
        type_='member'
    else:
        raise TypeError(f'Target expected to be Role or User type, got {type(target)!r}')
    data = {
        'target':target.id,
        'allow':allow,
        'deny':deny,
        'type':type_,
            }
    channel_id=channel.id
    overwrite_id=target.id
    return await bypass_request(client,METH_PUT,
        f'https://discordapp.com/api/v7/channels/{channel_id}/permissions/{overwrite_id}',
        data,)

async def permission_ow_delete(client,channel,overwrite,):
    channel_id=channel.id
    overwrite_id=overwrite.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/channels/{channel_id}/permissions/{overwrite_id}',
        )

async def channel_edit(client,channel,name='',topic='',nsfw=None,slowmode=None,user_limit=None,bitrate=None,type_=128,):
    data={}
    value=channel.type
    if name:
        if not 1<len(name)<101:
            raise ValueError(f'Invalid nam length {len(name)}, should be 2-100')
        data['name']=name
    
    if value in (0,5):
        if topic:
            if len(topic)>1024:
                raise ValueError(f'Invalid topic length {len(topic)}, should be 0-1024')
            data['topic']=topic
        
        if type_<128:
            if type_ not in (0,5):
                raise ValueError('You can switch chanel type only between only Text channel (0) and Guild news channel (5)')
            if type_!=value:
                data['type']=type_
        
    if value==0:
        if nsfw is not None:
            data['nsfw']=nsfw
            
        if slowmode is not None:
            if slowmode<0 or slowmode>120:
                raise ValueError(f'Invalid slowmode {slowmode}, should be 0-120')
            data['rate_limit_per_user']=slowmode

    elif value==2:
        if bitrate<8000 or bitrate>(96000,128000)['VIP' in channel.guild.feautres]:
            raise ValueError(f'Invalid bitrate {bitrate!r}, should be 8000-96000 (128000 for vip)')
        data['bitrate']=bitrate
        
        if user_limit:
            if user_limit<1 or user_limit>99:
                raise ValueError(f'Invalid user_limit {user_limit!r}, should be 0 for unlimited or 1-99')
            data['user_limit']=user_limit

    channel_id=channel.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/channels/{channel_id}',
        data,)

async def channel_delete(client,channel,):
    channel_id=channel.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/channels/{channel_id}',
        )

async def oauth2_token(client,):
    data = {
        'client_id'     : client.id,
        'client_secret' : client.secret,
        'grant_type'    : 'client_credentials',
        'scope'         : 'connections'
            }
    
    headers=multidict_titled()
    dict.__setitem__(headers,CONTENT_TYPE,['application/x-www-form-urlencoded'])
                
    return await bypass_request(client,METH_POST,
        'https://discordapp.com/api/oauth2/token',
        data,header=headers,)

async def invite_create(client,channel,):
    data = {
        'max_age'   : 60,
        'max_uses'  : 1,
        'temporary' : False,
        'unique'    : True,
            }
    channel_id=channel.id
    return await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/channels/{channel_id}/invites',
        data,)

async def invite_get_channel(client,channel,):
    channel_id=channel.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/channels/{channel_id}/invites',
        )

async def webhook_create(client,channel,name,avatar=b'',):
    data={'name':name}
    if avatar:            
        data['avatar']=bytes_to_base64(avatar)
            
    channel_id=channel.id
    return await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/channels/{channel_id}/webhooks',
        data,)

async def webhook_get_channel(client,channel,):
    channel_id=channel.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/channels/{channel_id}/webhooks',
        )

async def guild_create(client,name,icon=None,avatar=b'',
        region=VoiceRegion.eu_central,
        verification_level=VerificationLevel.medium,
        message_notification_level=MessageNotificationLevel.only_mentions,
        content_filter_level=ContentFilterLevel.disabled,
        roles=[],channels=[],):
        
    if client.is_bot and len(client.guilds)>9:
        raise ValueError('Bots cannot create a new server if they have more than 10.')

    if not (1<len(name)<101):
        raise ValueError(f'Guild\'s name\'s length can be between 2-100, got {len(name)}')
    
    data = {
        'name'                          : name,
        'icon'                          : None if icon is None else bytes_to_base64(avatar),
        'region'                        : region.id,
        'verification_level'            : verification_level.value,
        'default_message_notifications' : message_notification_level.value,
        'explicit_content_filter'       : content_filter_level.value,
        'roles'                         : roles,
        'channels'                      : channels,
            }

    data = await bypass_request(client,METH_POST,
        'https://discordapp.com/api/v7/guilds',
        data,)
    #we can create only partial, because the guild data is not completed usually
    return PartialGuild(data)

async def guild_get(client,guild_id,):
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}',
        )

async def guild_delete(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/guilds/{guild_id}',
        )

async def guild_edit(client,guild,name,icon=b'',): #keep it short
    data={'name':name}
    if icon is None:
        data['icon']=None
    elif icon:
        icon_data=bytes_to_base64(icon)
        ext=ext_from_base64(icon_data)
        if ext not in VALID_ICON_FORMATS:
            raise ValueError(f'Invalid icon type: {ext}')
        data['icon']=icon_data
    guild_id=guild.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/guilds/{guild_id}',
        data,)

async def audit_logs(client,guild,):
    data={'limit':100}
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/audit-logs',
        params=data,)

async def guild_bans(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/bans',
        )

async def guild_ban_add(client,guild,user_id,):
    data={'delete-message-days':0}
    guild_id=guild.id
    return await bypass_request(client,METH_PUT,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/bans/{user_id}',
        params=data,)

async def guild_ban_delete(client,guild,user_id,):
    guild_id=guild.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/bans/{user_id}',
        )

async def guild_ban_get(client,guild,user_id,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/bans/{user_id}',
        )

async def channel_move(client,*args,file=None,**kwargs):
    def http_channel_move_redirect(self,guild_id,data,reason):
        return bypass_request(client,METH_PATCH,
            f'https://discordapp.com/api/v7/guilds/{guild_id}/channels',data,
            )
    original=type(client.http).channel_move
    type(client.http).channel_move=http_channel_move_redirect
    coro=client.channel_move(*args,**kwargs)
    future=Future(client.loop)
    #skip 1 loop
    client.loop.call_at(0.0,future.__class__.set_result_if_pending,future,None)
    await future
    
    type(client.http).channel_move=original
    await coro

async def channel_create(client,guild,category=None,):
    data=cr_pg_channel_object(type_=0,name='tesuto-channel9')
    data['parent_id']=category.id if type(category) is ChannelCategory else None
    guild_id=guild.id
    return await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/channels',
        data,)

async def guild_embed_get(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/embed',
        )

async def guild_embed_edit(client,guild,value,):
    data={'enabled':value}
    guild_id=guild.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/embed',
        data,)

async def guild_embed_image(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/embed.png',
        params={'style':'shield'},decode=False,header={},)

async def guild_emojis(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/emojis',
        )

async def emoji_create(client,guild,name,image,):
    image=bytes_to_base64(image)
    name=''.join(re.findall('([0-9A-Za-z_]+)',name))
    if not (1<len(name)<33):
        raise ValueError(f'The length of the name can be between 2-32, got {len(name)}')
    
    data = {
        'name'      : name,
        'image'     : image,
        'role_ids'  : []
            }
        
    guild_id=guild.id
    return await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/emojis',
        data,)

async def emoji_get(client,guild,emoji_id,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/emojis/{emoji_id}',
        )

async def emoji_delete(client,guild,emoji,):
    guild_id=guild.id
    emoji_id=emoji.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/emojis/{emoji_id}',
        )

async def emoji_edit(client,guild,emoji,name,): #keep it short
    data={'name':name}
    guild_id=guild.id
    emoji_id=emoji.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/emojis/{emoji_id}',
        data,)

async def integration_get_all(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/integrations',
        )

async def invite_get_guild(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/invites',
        )

async def guild_user_delete(client,guild,user_id,):
    guild_id=guild.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/members/{user_id}',
        )

async def user_edit(client,guild,user,nick,mute=False,):
    guild_id=guild.id
    user_id=user.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/members/{user_id}',
        data={'nick':nick,'mute':mute},)

async def guild_user_add(client,guild,user,):
    guild_id=guild.id
    user_id=user.id
    return await bypass_request(client,METH_PUT,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/members/{user_id}',
        data={'access_token':user.access.access_token},)

async def user_role_add(client,user,role,):
    guild_id=role.guild.id
    user_id=user.id
    role_id=role.id
    return await bypass_request(client,METH_PUT,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
        )

async def user_role_delete(client,user,role,):
    guild_id=role.guild.id
    user_id=user.id
    role_id=role.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
        )

async def guild_prune(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/prune',
        params={'days':30},)

async def guild_prune_estimate(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/prune',
        params={'days':30},)

async def role_create(client,guild,name=None,permissions=None,color=None,
        separated=None,mentionable=None,reason=None,):

    data={}
    if name is not None:
        data['name']=name
    if permissions is not None:
        data['permissions']=permissions
    if color is not None:
        data['color']=color
    if separated is not None:
        data['hoist']=separated
    if mentionable is not None:
        data['mentionable']=mentionable

    guild_id=guild.id
    return await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/roles',
        data=data,)

async def role_move(client,role,new_position,):
    data=role.guild.roles.change_on_swich(role,new_position,key=lambda role,pos:{'id':role.id,'position':pos})
    guild_id=role.guild.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/roles',
        data=data,)

async def role_edit(client,role,color=None,separated=None,mentionable=None,
        name=None,permissions=None,):
    
    if color is None:
        color=role.color
    if separated is None:
        separated=role.separated
    if mentionable is None:
        mentionable=role.mentionable
    if name is None:
        name=role.name
    if permissions is None:
        permissions=role.permissions

    data = {
        'name'        : name,
        'permissions' : permissions,
        'color'       : color,
        'hoist'       : separated,
        'mentionable' : mentionable,
            }
    guild_id=role.guild.id
    role_id=role.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/roles/{role_id}',
        data=data,)

async def role_delete(client,role,):
    guild_id=role.guild.id
    role_id=role.id
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/roles/{role_id}',
        )


async def webhook_get_guild(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/webhooks',
        )

async def guild_widget_image(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/widget.png',
        params={'style':'shield'},decode=False,header={},)

async def invite_get(client,invite,):
    invite_code=invite.code
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/invites/{invite_code}',
        )

async def invite_delete(client,invite,):
    invite_code=invite.code
    return await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/invites/{invite_code}',
        )

async def user_info(client,access,):
    header=multidict_titled()
    header[AUTHORIZATION]=f'Bearer {access.access_token}'
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/users/@me',
        header=header,)

async def client_user(client,):
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/users/@me',
        )

async def channel_private_get_all(client,):
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/users/@me/channels',
        )

async def channel_private_create(client,user,):
    return await bypass_request(client,METH_POST,
        'https://discordapp.com/api/v7/users/@me/channels',
        data={'recipient_id':user.id},)

async def user_connections(client,access,):
    header=multidict_titled()
    header[AUTHORIZATION]=f'Bearer {access.access_token}'
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/users/@me/connections',
        header=header,)

async def user_guilds(client,access,):
    header=multidict_titled()
    header[AUTHORIZATION]=f'Bearer {access.access_token}'
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/users/@me/guilds',
        header=header,)

async def guild_get_all(client,):
    return await bypass_request(client,METH_GET,
        'https://discordapp.com/api/v7/users/@me/guilds',
        params={'after':0},)

async def user_get(client,user,):
    user_id=user.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/users/{user_id}',
        )

async def webhook_get(client,webhook,):
    webhook_id=webhook.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/webhooks/{webhook_id}',
        )

async def webhook_delete(client,webhook,):
    webhook_id=webhook.id
    return  bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/webhooks/{webhook_id}',
        )

async def webhook_edit(client,webhook,name,): #keep it short
    webhook_id=webhook.id
    return await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/webhooks/{webhook_id}',
        data={'name':name},)

async def webhook_get_token(client,webhook,):
    return await bypass_request(client,METH_GET,
        webhook.url,header={},)

async def webhook_delete_token(client,webhook,):
    return await bypass_request(client,METH_DELETE,
        webhook.url,header={},)

async def webhook_edit_token(client,webhook,name,): #keep it short
    return await bypass_request(client,METH_PATCH,
        webhook.url,
        data={'name':name},header={},)

async def webhook_execute(client,webhook,content,wait=False,):
    return await bypass_request(client,METH_POST,
        f'{webhook.url}?wait={wait:d}',
        data={'content':content},header={},)
    
async def guild_users(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/members',
        )

async def guild_regions(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/regions',
        )

async def guild_channels(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/channels',
        )

async def guild_roles(client,guild,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/roles',
        )

async def guild_user_get(client,guild,user_id,):
    guild_id=guild.id
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/members/{user_id}',
        )

async def guild_widget_get(client,guild_id,):
    return await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/guilds/{guild_id}/widget.json',
        header={},)

async def message_suppress_embeds(client,message,suppress=True,):
    message_id=message.id
    channel_id=message.channel.id
    return await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/channels/{channel_id}/messages/{message_id}/suppress-embeds',
        data={'suppress':suppress},)

async def channel_follow(client,source_channel,target_channel,):
    if source_channel.type!=5:
        raise ValueError(f'\'source_channel\' must be type 5, so news (announcements) channel, got {source_channel}')
    if target_channel.type not in ChannelText.INTERCHANGE:
        raise ValueError(f'\'target_channel\' must be type 0 or 5, so any guild text channel, got  {target_channel}')

    data = {
        'webhook_channel_id': target_channel.id,
            }

    channel_id=source_channel.id

    data = await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/channels/{channel_id}/followers',
        data,)
    webhook=Webhook._from_follow_data(data,source_channel,target_channel,client)
    return webhook

async def achievement_get(client,achievement_id,):
    application_id=client.application.id
        
    data = await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/applications/{application_id}/achievements/{achievement_id}',
        )
    
    return Achievement(data)
    

async def achievement_create(client,name,description,icon,secret=False,secure=False,):
    icon_data=bytes_to_base64(icon)
    ext=ext_from_base64(icon_data)
    if ext not in VALID_ICON_FORMATS_EXTENDED:
        raise ValueError(f'Invalid icon type: {ext}')

    data = {
        'name'          : {
            'default'   : name,
                },
        'description'   : {
            'default'   : description,
                },
        'secret'        : secret,
        'secure'        : secure,
        'icon'          : icon_data,
            }

    application_id=client.application.id
        
    data =  await bypass_request(client,METH_POST,
        f'https://discordapp.com/api/v7/applications/{application_id}/achievements',
        data=data,)
    
    return Achievement(data)

async def achievement_delete(client,achievement,):
    application_id=client.application.id
    achievement_id=achievement.id
    await bypass_request(client,METH_DELETE,
        f'https://discordapp.com/api/v7/applications/{application_id}/achievements/{achievement_id}',
        )

async def achievement_edit(client,achievement,name=None,description=None,secret=None,secure=None,icon=_spaceholder,):
    data={}
    if (name is not None):
        data['name'] = {
            'default'   : name,
                }
    if (description is not None):
        data['description'] = {
            'default'   : description,
                }
    if (secret is not None):
        data['secret']=secret
        
    if (secure is not None):
        data['secure']=secure
        
    if (icon is not _spaceholder):
        icon_data=bytes_to_base64(icon)
        ext=ext_from_base64(icon_data)
        if ext not in VALID_ICON_FORMATS_EXTENDED:
            raise ValueError(f'Invalid icon type: {ext}')
        data['icon']=icon_data

    application_id=client.application.id
    achievement_id=achievement.id
    
    data = await bypass_request(client,METH_PATCH,
        f'https://discordapp.com/api/v7/applications/{application_id}/achievements/{achievement_id}',
        data=data,)

    achievement._update_no_return(data)
    return achievement

async def achievement_get_all(client,):
    application_id=client.application.id
    
    data = await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/applications/{application_id}/achievements',
        )
    
    return [Achievement(achievement_data) for achievement_data in data]

async def user_achievement_update(client,user,achievement,percent_complete,):
    data={'percent_complete':percent_complete}
    
    user_id=user.id
    application_id=client.application.id
    achievement_id=achievement.id
    
    await bypass_request(client,METH_PUT,
        f'https://discordapp.com/api/v7/users/{user_id}/applications/{application_id}/achievements/{achievement_id}',
        data=data,)

async def user_achievements(client,access,):
    header=multidict_titled()
    header[AUTHORIZATION]=f'Bearer {access.access_token}'
    
    application_id=client.application.id
    
    data = await bypass_request(client,METH_GET,
        f'https://discordapp.com/api/v7/users/@me/applications/{application_id}/achievements',
        header=header,)
    
    return [Achievement(achievement_data) for achievement_data in data]


@ratelimit_commands
async def ratelimit_test0000(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0000') as RLT:
        try:
            achievements = await client.achievement_get_all()
        except BaseException as err:
            await RLT.send(repr(err))
        
        if not achievements:
            await RLT.send(repr('The application has no achievement'))
        
        achievement=achievements[0]
        achievement_id=achievement.id
        
        loop=client.loop
        
        tasks=[]
        for _ in range(6):
            task=Task(achievement_get(client,achievement_id),loop)
            tasks.append(task)
        
        await WaitTillAll(tasks,loop)
    #achievement_get limited. limit:5, reset:5
    
@ratelimit_commands
async def ratelimit_test0001(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0001') as RLT:
        try:
            achievements = await client.achievement_get_all()
        except BaseException as err:
            await RLT.send(repr(err))
        
        if len(achievements)<3:
            await RLT.send(repr('The application has less than 2 achievements'))
        
        achievement_1=achievements[0]
        achievement_2=achievements[1]
        
        achievement_id_1=achievement_1.id
        achievement_id_2=achievement_2.id
        
        loop=client.loop
        
        tasks=[]
        for _ in range(4):
            task=Task(achievement_get(client,achievement_id_1),loop)
            tasks.append(task)
            
            task=Task(achievement_get(client,achievement_id_2),loop)
            tasks.append(task)
        
        await WaitTillAll(tasks,loop)
    #achievement_get limited globally
    
@ratelimit_commands
async def ratelimit_test0002(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0002') as RLT:
        image_path=join(os.path.abspath('.'),'images','0000000C_touhou_komeiji_koishi.png')
        with (await AsyncIO(image_path)) as file:
            image = await file.read()
        
        loop=client.loop
        
        tasks=[]
        names=('Yura','Hana','Neko','Kaze','Scarlet','Yukari')
        for name in names:
            description=name+'boroshi'
            task=Task(achievement_create(client,name,description,image),loop)
            tasks.append(task)
            
        await WaitTillAll(tasks,loop)
        
        for task in tasks:
            try:
                achievement=task.result()
            except:
                pass
            else:
                await client.achievement_delete(achievement.id)
    #achievement_create limited. limit:5, reset:5, globally
    
@ratelimit_commands
async def ratelimit_test0003(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0003') as RLT:
        image_path=join(os.path.abspath('.'),'images','0000000C_touhou_komeiji_koishi.png')
        with (await AsyncIO(image_path)) as file:
            image = await file.read()
        
        achievements=[]
        for name in ('Cake','Neko'):
            description=name+' are love'
            achievement = await client.achievement_create(name,description,image)
            achievements.append(achievement)
        
        loop=client.loop
        
        tasks = []
        for achievement in achievements:
            task = Task(achievement_delete(client,achievement),loop)
            tasks.append(task)
        
        await WaitTillAll(tasks,loop)
    #achievement_delete limited. limit:5, reset:5, globally

@ratelimit_commands
async def ratelimit_test0004(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0004') as RLT:
        image_path=join(os.path.abspath('.'),'images','0000000C_touhou_komeiji_koishi.png')
        with (await AsyncIO(image_path)) as file:
            image = await file.read()
        
        achievement = await client.achievement_create('Cake','Nekos are love',image)
        
        loop=client.loop
        tasks = []
        
        task = Task(achievement_edit(client,achievement,name='Hana'),loop)
        tasks.append(task)
        
        task = Task(achievement_edit(client,achievement,name='Phantom'),loop)
        tasks.append(task)
        
        await WaitTillAll(tasks,loop)
        await client.achievement_delete(achievement)
    #achievement_edit limited. limit:5, reset:5
    
@ratelimit_commands
async def ratelimit_test0005(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0005') as RLT:
        image_path=join(os.path.abspath('.'),'images','0000000C_touhou_komeiji_koishi.png')
        with (await AsyncIO(image_path)) as file:
            image = await file.read()
        
        achievements=[]
        for name in ('Kokoro','Koishi'):
            description='UwUwUwU'
            achievement = await client.achievement_create(name,description,image)
            achievements.append(achievement)
    
        loop=client.loop
        tasks = []
        for achievement in achievements:
            task = Task(achievement_edit(client,achievement,name='Yura'),loop)
            tasks.append(task)
        
        await WaitTillAll(tasks,loop)
        
        for achievement in achievements:
            await client.achievement_delete(achievement)
    #achievement_edit limited globally

@ratelimit_commands
async def ratelimit_test0006(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0006') as RLT:
        image_path=join(os.path.abspath('.'),'images','0000000C_touhou_komeiji_koishi.png')
        with (await AsyncIO(image_path)) as file:
            image = await file.read()
        
        achievement = await achievement_create(client,'Kokoro','is love',image)
        await achievement_get(client,achievement.id)
        await achievement_edit(client,achievement,name='Yurika')
        await achievement_delete(client,achievement)
    
    # achievement_create, achievement_get, achievement_edit, achievement_delete are NOT grouped
    
@ratelimit_commands
async def ratelimit_test0007(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0007') as RLT:
        loop=client.loop
        tasks = []
        for _ in range(2):
            task = Task(achievement_get_all(client),loop)
            tasks.append(task)
        
        await WaitTillAll(tasks,loop)
    
    #achievement_get_all limited. limit:5, reset:5, globally

@ratelimit_commands
async def ratelimit_test0008(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0008') as RLT:
        image_path=join(os.path.abspath('.'),'images','0000000C_touhou_komeiji_koishi.png')
        with (await AsyncIO(image_path)) as file:
            image = await file.read()
        
        achievement = await client.achievement_create('Koishi','Kokoro',image,secure=True)
        
        try:
            await user_achievement_update(client,client.owner,achievement,100)
        finally:
            await client.achievement_delete(achievement)
    
    # DiscordException NOT FOUND (404), code=10029: Unknown Entitlement
    # user_achievement_update limited. Limit : 5, reset : 5.
    
@ratelimit_commands
async def ratelimit_test0009(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0009') as RLT:
        image_path=join(os.path.abspath('.'),'images','0000000C_touhou_komeiji_koishi.png')
        with (await AsyncIO(image_path)) as file:
            image = await file.read()
        
        achievement = await client.achievement_create('Koishi','Kokoro',image,secure=True)
        await sleep(2.0,client.loop) # wait some time this time
        
        try:
            await user_achievement_update(client,client.owner,achievement,100)
        finally:
            await client.achievement_delete(achievement)

    # DiscordException NOT FOUND (404), code=10029: Unknown Entitlement
    
@ratelimit_commands
async def ratelimit_test0010(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0010') as RLT:
        image_path=join(os.path.abspath('.'),'images','0000000C_touhou_komeiji_koishi.png')
        with (await AsyncIO(image_path)) as file:
            image = await file.read()
        
        achievement = await client.achievement_create('Koishi','Kokoro',image) #no just a normal one
        
        try:
            await user_achievement_update(client,client.owner,achievement,100)
        finally:
            await client.achievement_delete(achievement)
    
    # DiscordException FORBIDDEN (403), code=40001: Unauthorized

@ratelimit_commands
async def ratelimit_test0011(client,message,content):
    if not client.is_owner(message.author):
        return
    
    with RLTCTX(client,message.channel,'ratelimit_test0011') as RLT:
        image_path=join(os.path.abspath('.'),'images','0000000C_touhou_komeiji_koishi.png')
        with (await AsyncIO(image_path)) as file:
            image = await file.read()
        
        achievement = await client.achievement_create('Koishi','Kokoro',image,secure=True)
        
        loop=client.loop
        tasks=[]
        for member in client.application.owner.members:
            user = member.user
            task=Task(user_achievement_update(client,user,achievement,100),loop)
            tasks.append(task)
        
        await WaitTillAll(tasks,loop)
        await client.achievement_delete(achievement)
    
    # DiscordException NOT FOUND (404), code=10029: Unknown Entitlement
    #limited globally

class check_is_owner(object):
    __slots__=('client', )
    def __init__(self,client):
        self.client=client
    
    def __call__(self,message):
        return self.client.is_owner(message.author)
    
@ratelimit_commands
async def ratelimit_test0012(client,message,content):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0012') as RLT:
        await client.message_create(channel, (
            'Please authorize yourself and resend the redirected url after it\n'
            'https://discordapp.com/oauth2/authorize?client_id=486565096164687885'
            '&redirect_uri=https%3A%2F%2Fgithub.com%2FHuyaneMatsu'
            '&response_type=code&scope=identify%20applications.store.update'))
        
        try:
            message = await wait_for_message(client,channel,check_is_owner(client),60.)
        except TimeoutError:
            await RLT.send('Timeout meanwhile waiting for redirect url.')
    
        Task(client.message_delete(message),client.loop)
        try:
            result=parse_oauth2_redirect_url(message.content)
        except ValueError:
            await RLT.send('Bad redirect url.')
        
        access = await client.activate_authorization_code(*result,['identify', 'applications.store.update'])
        
        if access is None:
            await RLT.send('Too old redirect url.')
        
        await user_achievements(client,access)
    #DiscordException UNAUTHORIZED (401): 401: Unauthorized
    # no limit data provided

@ratelimit_commands
async def ratelimit_test0013(client,message,content):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0013') as RLT:
        if channel.guild is None:
            await RLT.send('Please use this command at a guild.')
        
        if not channel.cached_permissions_for(client).can_administrator:
            await RLT.send('I need admin permission to complete this command.')
        
        old_message=None
        old_limit=int((time_now()-1209610.)*1000.-DISCORD_EPOCH)<<22
        
        while True:
            messages_ = await client.message_logs(channel,after=old_limit)
            for message_ in messages_:
                if message_.author==client:
                    old_message=message_
                    break
            
            if (old_message is not None):
                break
            
            if len(messages_)<100:
                break
            
            old_limit=messages_[99].id
            continue
        
        if old_message is None:
            await RLT.send('Getting old message failed')
        
        messages = []
        for index in range(6):
            message_ = await client.message_create(channel,f'testing ratelimit: message {index}')
            messages.append(message_)
        
        loop=client.loop
        tasks = []
        
        for message_ in messages:
            task=Task(message_delete(client,message_),loop)
            tasks.append(task)
        
        task=Task(message_delete(client,old_message),loop)
        tasks.append(task)
        
        await WaitTillAll(tasks,loop)
    
    # message_delete (own new) unlimited
    # message_delete (own new) not limtied with message_delete (own old)
    # message_delete limited sometimes with new/own group
    
@ratelimit_commands
async def ratelimit_test0014(client,message,content):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0014') as RLT:
        if channel.guild is None:
            await RLT.send('Please use this command at a guild.')
    
        if not channel.cached_permissions_for(client).can_administrator:
            await RLT.send('I need admin permission to complete this command.')
        
        other_client=None
        for client_ in channel.clients:
            if client_ is client:
                continue
            
            if channel.cached_permissions_for(client_).can_send_messages:
                other_client=client_
                break
        
        if other_client is None:
            await RLT.send('I Dont see any other clients at this channel, with `send_messages` permission.')
        
        old_message=None
        
        old_limit=int((time_now()-1209610.)*1000.-DISCORD_EPOCH)<<22
        
        while True:
            messages_ = await client.message_logs(channel,after=old_limit)
            for message_ in messages_:
                if message_.author==client:
                    old_message=message_
                    break
            
            if (old_message is not None):
                break
            
            if len(messages_)<100:
                break
            
            old_limit=messages_[99].id
            continue
        
        if old_message is None:
            await RLT.send('Getting old message failed')
        
        messages = []
        for index in range(6):
            message_ = await other_client.message_create(channel,f'testing ratelimit: message {index}')
            messages.append(message_)
        
        loop=client.loop
        tasks = []
        
        for message_ in messages:
            task=Task(message_delete(client,message_),loop)
            tasks.append(task)
        
        task=Task(message_delete(client,old_message),loop)
        tasks.append(task)
        
        await WaitTillAll(tasks,loop)
    
    # message_delete (other new) unlimited
    # message_delete (other new) not limtied with message_delete (own old)
    # message_delete limited sometimes with new/own group
    
@ratelimit_commands
async def ratelimit_test0015(client,message,content):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0015') as RLT:
        if channel.guild is None:
            await RLT.send('Please use this command at a guild.')
        
        if not channel.cached_permissions_for(client).can_administrator:
            await RLT.send('I need admin permission to complete this command.')
    
        other_client=None
        for client_ in channel.clients:
            if client_ is client:
                continue
            
            permissions = channel.cached_permissions_for(client_)
            if permissions.can_administrator:
                continue
            
            if not permissions.can_manage_messages:
                continue
            
            other_client=client_
            break
            
        if other_client is None:
            await RLT.send(
                'I need an another client without admin permisison, but with '
                'manage messages permission at this channel to complete this '
                'command.')
        
        messages = []
        for index in range(6):
            message_ = await client.message_create(channel,f'testing ratelimit: message {index}')
            messages.append(message_)
        
        loop=client.loop
        tasks = []
        
        for message_ in messages:
            task=Task(message_delete(other_client,message_),loop)
            tasks.append(task)
        
        await WaitTillAll(tasks,loop)
    
    # deleting without admin before 2 week is unlimited
    # sometimes limited too propably
    
@ratelimit_commands
async def ratelimit_test0016(client,message,content):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0016') as RLT:
        if channel.guild is None:
            await RLT.send('Please use this command at a guild.')
        
        if not channel.cached_permissions_for(client).can_administrator:
            await RLT.send('I need admin permission to complete this command.')
        
        old_message_own=None
        old_message_other=None
        
        old_limit=int((time_now()-1209610.)*1000.-DISCORD_EPOCH)<<22
        while True:
            messages_ = await client.message_logs(channel,before=old_limit)
            for message_ in messages_:
                if message_.author==client:
                    if (old_message_own is not None):
                        continue
                        
                    old_message_own=message_
                    if (old_message_other is not None):
                        break
                    
                    continue
                
                else:
                    if (old_message_other is not None):
                        continue
                    
                    old_message_other=message_
                    if (old_message_own is not None):
                        break
                    
                    continue
            
            if (old_message_own is not None) and (old_message_other is not None):
                break
            
            if len(messages_)<100:
                break
            
            old_limit=messages_[99].id
            continue
        
        if old_message_own is None:
            await RLT.send('Did not find old message from me.')
        
        if old_message_other is None:
            await RLT.send('Did not find old message from someone else.')
        
        loop=client.loop
        tasks = []
        
        task=Task(message_delete(client,old_message_own),loop)
        tasks.append(task)
        task=Task(message_delete(client,old_message_own),loop)
        tasks.append(task)
        
        await WaitTillAll(tasks,loop)
    # after 2 weeks message delete own and other is limited as same.

@ratelimit_commands
async def ratelimit_test0017(client,message,content):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0017') as RLT:
        if channel.guild is None:
            await RLT.send('Please use this command at a guild.')
        
        if not channel.cached_permissions_for(client).can_administrator:
            await RLT.send('I need admin permission to complete this command.')
        
        old_limit=int((time_now()-1209610.)*1000.-DISCORD_EPOCH)<<22
        
        messages = await client.message_logs(channel,before=old_limit)
        
        loop=client.loop
        for message_ in messages:
            await Task(message_delete(client,message_),loop)
    
    # even deleting 100 message does not changes limit
    # well, we discovered already, that it is only sometimes limited
    
@ratelimit_commands
async def ratelimit_test0018(client,message,content):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0018') as RLT:
        if channel.guild is None:
            await RLT.send('Please use this command at a guild.')
    
        if not channel.cached_permissions_for(client).can_administrator:
            await RLT.send('I need admin permission to complete this command.')
        
        old_message=None
        # check 2 weeks
        old_limit=int((time_now()-1209610.)*1000.-DISCORD_EPOCH)<<22
        
        while True:
            messages_ = await client.message_logs(channel,before=old_limit)
            for message_ in messages_:
                if message_.author==client:
                    old_message=message_
                    break
            
            if (old_message is not None):
                break
            
            if len(messages_)<100:
                break
            
            old_limit=messages_[99].id
            continue
        
        if old_message is None:
            await RLT.send('Getting old message failed')
    
        await Task(message_delete(client,old_message),client.loop)
    
    # after 2 week + own : limit: 1s / 3 request
    
@ratelimit_commands
async def ratelimit_test0019(client,message,content):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0019') as RLT:
        if channel.guild is None:
            await RLT.send('Please use this command at a guild.')
        
        if not channel.cached_permissions_for(client).can_administrator:
            await RLT.send('I need admin permission to complete this command.')
        
        old_message=None
        # check 2 weeks
        old_limit=int((time_now()-1209610.)*1000.-DISCORD_EPOCH)<<22
        
        while True:
            messages_ = await client.message_logs(channel,before=old_limit)
            for message_ in messages_:
                if message_.author!=client:
                    old_message=message_
                    break
            
            if (old_message is not None):
                break
            
            if len(messages_)<100:
                break
            
            old_limit=messages_[99].id
            continue
        
        if old_message is None:
            await RLT.send('Getting old message failed')
    
        await Task(message_delete(client,old_message),client.loop)
    
    # after 2 week, other limit: 120s / 30 request

ratelimit_test0020_OK       = BUILTIN_EMOJIS['ok_hand']
ratelimit_test0020_CANCEL   = BUILTIN_EMOJIS['x']
ratelimit_test0020_EMOJIS   = (ratelimit_test0020_OK, ratelimit_test0020_CANCEL)

class ratelimit_test0020_checker(object):
    __slots__ = ('client',)
    
    def __init__(self, client):
        self.client=client
    
    def __call__(self, emoji, user):
        if not self.client.is_owner(user):
            return False
        
        if emoji not in ratelimit_test0020_EMOJIS:
            return False
        
        return True

@ratelimit_commands
async def ratelimit_test0020(client,message):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0020') as RLT:
        if channel.guild is None:
            await RLT.send('Please use this command at a guild.')
            
        if not channel.cached_permissions_for(client).can_administrator:
            await RLT.send('I need admin permission to complete this command.')
        
##        channels=[]
##
##        category=channel.category
##        if type(category) is ChannelCategory:
##            for channel in category.channels:
##                if type(channel) is ChannelText:
##                    channels.append(channel)
##        else:
##            category.append(channel)
##
##        messages=[]
##        for day in range(41):
##            
##            before_ori= int((time_now()-(day  )*86400.+100.)*1000.-DISCORD_EPOCH)<<22
##            after_ori = int((time_now()-(day+1)*86400.-100.)*1000.-DISCORD_EPOCH)<<22
##            
##            message_own=None
##            message_other=None
##            
##            for channel_ in channels:
##                before=before_ori
##                while True:
##                    messages_ = await client.message_logs(channel_,after=after_ori,before=before)
##                    print(after_ori,before,messages_)
##                    for message_ in messages_:
##                        if message_.author==client:
##                            if message_own is None:
##                                message_own=message_
##                                if (message_other is not None):
##                                    break
##                        else:
##                            if message_other is None:
##                                message_other=message_
##                                if (message_own is not None):
##                                    break
##                    
##                    if (message_own is not None) and (message_other is not None):
##                        break
##                    
##                    if len(messages_)!=100:
##                        break
##                    
##                    before=messages_[99].id
##                    continue
##                    
##                if message_own is None:
##                    continue
##                    
##                if message_other is None:
##                    continue
##                
##                break
##            
##            messages.append((message_own,message_other,),)
        
        target_time=int((time_now()-40*86400.)*1000.-DISCORD_EPOCH)<<22
        async for message_ in client.message_iterator(channel):
            if message_.id>target_time:
                continue
            break
        
        now=time_now()
        time_bounds=[]
        for day in range(41):
            before= int((now-(day  )*86400.+100.)*1000.-DISCORD_EPOCH)<<22
            after = int((now-(day+1)*86400.-100.)*1000.-DISCORD_EPOCH)<<22
            time_bounds.append((before,after),)
        
        messages=[]
        for day in range(41):
            messages.append((None,None),)
        
        for message_ in channel.messages:
            for day,(before,after) in enumerate(time_bounds):
                if message_.id>before:
                    continue
                
                if message_.id<after:
                    continue
                
                message_own,message_other=messages[day]
                if (message_own is not None) and (message_other is not None):
                    break
                
                if message_.author==client:
                    if message_own is None:
                        messages[day]=(message_,message_other)
                else:
                    if message_other is None:
                        messages[day]=(message_own,message_)
                
                break
        
        result=['```\nday | own | other\n']
        for day,(message_own, message_other) in enumerate(messages):
            result.append(f'{day:>3} | {("YES", " NO")[message_own is None]} | {("YES"," NO")[message_other is None]}\n')
        result.append('```\nShould we start?')
        embed=Embed('Found messages',''.join(result))
        
        message = await client.message_create(channel,embed=embed)
        
        for emoji in ratelimit_test0020_EMOJIS:
            await client.reaction_add(message,emoji)
        
        try:
            emoji, _ = await wait_for_reaction(client, message, ratelimit_test0020_checker(client), 40.)
        except TimeoutError:
            emoji = ratelimit_test0020_CANCEL
            
        await client.reaction_clear(message)
        
        if emoji is ratelimit_test0020_CANCEL:
            embed.add_footer('ratelimit_test0020 cancelled')
            await client.message_edit(message,embed=embed)
            raise CancelledError()
        
        if emoji is ratelimit_test0020_OK:
            loop=client.loop
            for day,(message_own, message_other) in enumerate(messages):
                if (message_own is not None):
                    RLT.write(f'day {day}, own:')
                    await Task(message_delete(client,message_own),loop)
                
                if (message_other is not None):
                    RLT.write(f'day {day}, other:')
                    await Task(message_delete(client,message_other),loop)
            
            return
            
        # no more case
        
@ratelimit_commands
async def ratelimit_test0021(client,message):
    if not client.is_owner(message.author):
        return
    
    channel = message.channel
    with RLTCTX(client,channel,'ratelimit_test0021') as RLT:
        if channel.guild is None:
            await RLT.send('Please use this command at a guild.')
            
        if not channel.cached_permissions_for(client).can_administrator:
            await RLT.send('I need admin permission to complete this command.')
            
        messages=[]
        for index in range(2):
            message_ = await client.message_create(channel,f'testing ratelimit: message {index}')
            messages.append(message_)
        
        await Task(message_delete_multiple(client,messages),client.loop)


