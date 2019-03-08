# -*- coding: utf-8 -*-
from hata.exceptions import HTTPException,Forbidden
from hata.parsers import EVENTS,default_event
from hata.prettyprint import pchunkify,pretty_print
from hata.events import pagination
from hata.others import cchunkify

class dispatch_tester:
    channel=None

    @classmethod
    async def here(self,client,message,content):
        if message.author is not client.owner:
            return
        if message.channel is self.channel:
            try:
                await client.message_create(message.channel,'Current channel removed')
            except (HTTPException,Forbidden):
                return
            self.channel=None
        else:
            try:
                await client.message_create(message.channel,f'Channel set to {message.channel.name} {message.channel.id}')
            except (HTTPException,Forbidden):
                return
            self.channel=message.channel
            
    @classmethod
    async def switch(self,client,message,content):
        if message.author is not client.owner or not (5<len(content)<50):
            return
        if content not in EVENTS.defaults:
            await client.message_create(message.channel,f'Invalid dispatcher: {content}')
            return
        event=getattr(self,content,None)
        if event is None:
            await client.message_create(message.channel,f'Unallowed/undefined dispatcher: {content}')
            return
        
        actual=getattr(client.events,content)

        if actual is default_event:
            try:
                await client.message_create(message.channel,'Event set')
            except (HTTPException,Forbidden):
                return
            setattr(client.events,content,event)
        else:
            try:
                await client.message_create(message.channel,'Event removed')
            except (HTTPException,Forbidden):
                return
            setattr(client.events,content,default_event)

    @classmethod
    async def client_edit(self,client,old):
        if self.channel is None:
            return
        result=[]
        result.append(f'Me, {client:f} got edited')
        for key,value in old.times():
            result.append(f'- {key} got changed: {value} -> {getattr(client,key)}')

        try:
            await client.message_create(self.channel,'\n'.join(result))
        except (HTTPException,Forbidden):
            self.channel=None

    @classmethod
    async def message_delete(self,client,message):
        text=pretty_print(message)
        text.insert(0,f'Message {message.id} got deleted')
        pages=[{'content':chunk} for chunk in cchunkify(text)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def message_edit(self,client,message,old):
        if self.channel is None:
            return
        result=[f'Message {message.id} got edited']

        for key,value in old.items():
            if key in ('pinned','activity_party_id','everyone_mention'): 
                result.append(f'- {key} got changed: {value!r} -> {getattr(message,key)!r}')
                continue
            if key in ('edited',):
                if value is None:
                    result.append(f'- {key} got changed: None -> {getattr(message,key):%Y.%m.%d-%H:%M:%S}')
                else:
                    result.append(f'- {key} got changed: {value:%Y.%m.%d-%H:%M:%S} -> {getattr(message,key):%Y.%m.%d-%H:%M:%S}')
                continue
            if key in ('application','activity','attachments','embeds'):
                result.append(f'- {key} got changed:')
                if value is None:
                    result.append('From None')
                else:
                    result.extend(pretty_print(value))
                value=getattr(message,key)
                if value is None:
                    result.append('To None')
                else:
                    result.extend(pretty_print(value))
                continue
            if key in ('content',):
                result.append(f'- {key} got changed from:')
                content=value
                break_=False
                while True:
                    content_ln=len(content)
                    result.append(f'- content: (len={content_ln})')
                    if content_ln>500:
                        content=content[:500].replace('`','\\`')
                        result.append(f'--------------------\n{content}\n... +{content_ln-500} more\n--------------------')
                    else:
                        content=content.replace('`','\\`')
                        result.append(f'--------------------\n{content}\n--------------------')
                    if break_:
                        break
                    break_=True
                    content=getattr(message,key)
                    result.append('To:')
                continue
            if key in ('user_mentions','role_mentions'):
                result.append(f'- {key} got changed from:')
                break_=False
                while True:
                    if vlaue is None:
                        resutl.append('    - None -')
                    else:
                        for index,obj in enumerate(1,value):
                            result.append(f'    - {obj.name} {obj.id}')
                if break_:
                    break
                result.append('To:')
                value=getattr(message,key)
                break_=True
                continue
            
        text=cchunkify(result)
        pages=[{'content':chunk} for chunk in text]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def reaction_clear(self,client,message,old):
        if self.channel is None:
            return
        text=pretty_print(old)
        text.insert(0,f'Reactions got cleared from message {message.id}:')
        pages=[{'content':chunk} for chunk in cchunkify(text)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def user_presence_update(self,client,user,old):
        result=[f'Presence update on user: {user:f} {user.id}']
        try:
            status=old['status']
        except KeyError:
            pass
        else:
            result.append(f'- status changed: {status} -> {user.status}')

        try:
            activity=old['activity']
        except KeyError:
            pass
        else:
            if type(activity) is dict:
                result.append('activity got updated:')
                for key,value in activity.items():
                    result.append(f'- {key} : {value} -> {getattr(user.activity,key)}')
            else:
                result.append('activity changed from:')
                result.extend(pretty_print(activity))
                result.append('To:')
                result.extend(pretty_print(user.activity))

        pages=[{'content':chunk} for chunk in cchunkify(result)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def user_edit(self,client,user,old):
        result=[f'A user got updated: {user:f} {user.id}']
        for key,value in old. items():
            result.append(f'- {key} : {value} -> {getattr(user,key)}')

        pages=[{'content':chunk} for chunk in cchunkify(result)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions
    
    @classmethod
    async def user_profile_edit(self,client,user,old,guild):
        result=[f'{user:f} {user.id} profile got edited at guild {guild.name!r} {guild.id}:']
        profile=user.guild_profiles[guild]
        for key,value in old.items():
            if key in ('nick',):
                result.append(f'{key} changed: {value!r} -> {getattr(profile,key)!r}')
                continue
            if key=='roles':
                removed=value[0]
                if removed:
                    result.append(f'Roles removed: ({len(removed)}')
                    for role in removed:
                        result.append(f'- {role.name} {role.id}')
                added=value[1]
                if added:
                    result.append(f'Roles added: ({len(added)})')
                    for role in added:
                        result.append(f'- {role.name} {role.id}')
            continue


        pages=[{'content':chunk} for chunk in cchunkify(result)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def channel_delete(self,client,channel):
        text=f'```\nA channel got deleted: {channel.name} {channel.id}\nchannel type: {channel.__class__.__name__} ({channel.type})```'
        pages=[{'content':text}]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def channel_edit(self,client,channel,old):
        result=[f'A channel got edited: {channel.name} {channel.id}\nchannel type: {channel.__class__.__name__} ({channel.type})']
        for key,value in old.items():
            result.append(f'{key} changed: {value!r} -> {getattr(channel,key)!r}')
        pages=[{'content':chunk} for chunk in cchunkify(result)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def channel_create(self,client,channel):
        result=pretty_print(channel)
        result.insert(0,f'A channel got created: {channel.name} {channel.id}\nchannel type: {channel.__class__.__name__} ({channel.type})')
        pages=[{'content':chunk} for chunk in cchunkify(result)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def channel_pin_update(self,client,channel):
        text=f'```\nA channel\'s pins changed: {channel.name} {channel.id}\nchannel type: {channel.__class__.__name__} ({channel.type})```'
        pages=[{'content':text}]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    #need connections:
    #channel_group_user_add
    #channel_group_user_delete
        
    @classmethod
    async def emoji_edit(self,client,guild,changes):
        if self.channel is None:
            return
    
        result=[]
        for modtype,emoji,diff in modifications:
            if modtype=='n':
                result.append(f'New emoji: "{emoji.name}" : {emoji}')
                continue
            if modtype=='d':
                result.append(f'Deleted emoji: "{emoji.name}" : {emoji}')
                continue
            if modtype=='e':
                result.append(f'Emoji edited: "{emoji.name}" : {emoji}\n')
                for key,value in diff.items():
                    result.append(f'- {key}: {value} -> {getattr(emoji,key)}')
                continue
            raise RuntimeError #bugged?
        
        pages=[{'content':chunk} for chunk in chunkify(result)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def guild_user_add(self,client,guild,user):
        if guild.owner  is not client.owner:
            return
        channel=guild.system_channel
        if channel is None:
            return
        await client.message_create(channel,f'Welcome to the Guild {user:f}!\nThe guild reached {guild.user_count} members!')

    @classmethod
    async def guild_user_delete(self,client,guild,user,profile):
        if guild.owner is not client.owner:
            return
        channel=guild.system_channel
        if channel is None:
            return
        await client.message_create(channel,f'Bai bai {user:f}! with your {len(profile.roles)} roles.\nThe guild is down to {guild.user_count} members!')
        if guild in user.guild_profiles:
            raise RuntimeError
        
    @classmethod
    async def guild_create(self,client,guild):
        if self.channel is None:
            return
        result=pretty_print(guild)
        result.insert(0,f'Guild created: {guild.id}')
        pages=[{'content':chunk} for chunk in cchunkify(result)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    #Unknown:
    #guild_sync
        
    @classmethod
    async def guild_edit(self,client,guild,old):
        if self.channel is None:
            return
        result=[f'A guild got edited {guild.name} {guild.id}']
        for key,value in old.items():
            if key in ('name','icon','splash','user_count','afk_timeout','available'):
                result.append(f' - {key} : {value} - > {getattr(guild,key)}')
                continue
            if key in ('verification_level','message_notification','mfa','content_filter','region'):
                other=getattr(guild,key)
                result.append(f' - {key} : {value!s} {value.value} -> {other!s} {other.value}')
                continue
            if key in ('features',):
                result.append(f'{key}:')
                removed=value[0]
                if removed:
                    result.append(f'- {key} removed: ({len(removed)}')
                    for subvalue in removed:
                        result.append(f'- {subvalue.value}')
                added=value[1]
                if added:
                    result.append(f'- {key} added: ({len(added)})')
                    for subvalue in added:
                        result.append(f'- {subvalue.value}')
                continue
            if key in ('system_channel','afk_channel','widget_channel','embed_channel'):
                other=getattr(guild,key)
                if value is None:
                    result.append(f'- {key} : None -> {other.name} {other.id}')
                elif other is None:
                    result.append(f'- {key} : {value.name} {value.id} -> None')
                else:
                    result.append(f'- {key} : {value.name} {value.id} -> {other.name} {other.id}')
                continue

            if key in ('owner',):
                other=getattr(guild,'owner')
                result.append(f'- {key} : {value:f} {value.id} -> {other:f} {other.id}')
                continue
            raise RuntimeError(key)

        pages=[{'content':chunk} for chunk in cchunkify(result)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions
        
    @classmethod
    async def guild_delete(self,client,guild):
        if self.channel is None:
            return
        result=pretty_print(guild)
        result.insert(0,f'Guild deleted {guild.id}')
        pages=[{'content':chunk} for chunk in cchunkify(result)]
        pagination(client,self.channel,pages,120.) #does not raises exceptions


    @classmethod
    async def guild_ban_add(self,client,guild,user):
        if self.channel is None:
            return
        text=f'```\nUser {user:f} {user.id} got banned at {guild.name} {guild.id}.```'
        pages=[{'content':text}]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    @classmethod
    async def guild_ban_delete(self,client,guild,user):
        if self.channel is None:
            return
        text=f'```\nUser {user:f} {user.id} got UNbanned at {guild.name} {guild.id}.```'
        pages=[{'content':text}]
        pagination(client,self.channel,pages,120.) #does not raises exceptions

    #Auto dispatched:
    #guild_user_chunk
    #Need integartion:
    #integration_edit