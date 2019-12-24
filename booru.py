# -*- coding: utf-8 -*-
import re
from collections import deque

from hata.embed import Embed
from hata.parsers import eventlist
from hata.color import Color
from hata.emoji import BUILTIN_EMOJIS
from hata.events import Timeouter, Cooldown, GUI_STATE_READY,               \
    GUI_STATE_SWITCHING_PAGE, GUI_STATE_CANCELLING, GUI_STATE_CANCELLED,    \
    GUI_STATE_SWITCHING_CTX

from hata.futures import Task
from hata.exceptions import DiscordException

from tools import BeautifulSoup, choose, pop_one, CooldownHandler, mark_as_async, choose_notsame
from help_handler import KOISHI_HELP_COLOR, KOISHI_HELPER

BOORU_COLOR=Color.from_html('#138a50')

SAFE_BOORU='http://safebooru.org/index.php?page=dapi&s=post&q=index&tags='
NSFW_BOORU='http://gelbooru.com/index.php?page=dapi&s=post&q=index&tags='

class cached_booru_command(object):
    _FILTER='solo+-underwear+-sideboob+-pov_feet+-underboob+-upskirt+-sexually_suggestive+-ass+-bikini+-6%2Bgirls+-comic+-greyscale+'
    __slots__=('_tag_name', 'title', 'urls',)
    def __init__(self,title,tag_name):
        self._tag_name=tag_name
        self.title=title
        self.urls=None
        
    async def __call__(self,client,message,content):
        urls=self.urls
        if urls is None:
            await self._request_urls(client)
            urls=self.urls
            if urls is None:
                await client.message_create(message.channel,embed=Embed('Booru is unavailable',color=BOORU_COLOR))
                return

        await ShuffledShelter(client,message.channel,urls,False,self.title)

    async def _request_urls(self,client):
        url=''.join([SAFE_BOORU,self._FILTER,self._tag_name])
        async with client.http.request_get(url) as response:
            result = await response.read()
        if response.status!=200:
            return
        soup=BeautifulSoup(result,'lxml')
        self.urls=[post['file_url'] for post in soup.find_all('post')]

booru_commands=eventlist()


class ShuffledShelter(object):
    CYCLE   = BUILTIN_EMOJIS['arrows_counterclockwise']
    BACK    = BUILTIN_EMOJIS['leftwards_arrow_with_hook']
    EMOJIS  = (CYCLE, BACK)
    
    __slots__ = ('canceller', 'channel', 'client', 'history', 'history_step',
        'message', 'pop', 'task_flag', 'timeouter', 'title', 'urls')
    
    async def __new__(cls,client,channel,urls,pop,title='Link'):
        if not urls:
            await client.message_create(channel,embed=Embed('No result'))
            return
        
        self=object.__new__(cls)
        self.client=client
        self.channel=channel
        self.canceller=self.__class__._canceller
        self.task_flag=GUI_STATE_READY
        self.urls=urls
        self.pop=pop
        self.title=title
        self.timeouter=None
        history=deque(maxlen=100)
        self.history=history
        self.history_step=1
        
        
        url=pop_one(urls) if pop else choose(urls)
        history.append(url)
        
        embed=Embed(title,color=BOORU_COLOR,url=url)
        embed.add_image(url)
        
        message = await client.message_create(channel,embed=embed)
        self.message=message
        
        if (len(urls)==(0 if pop else 1)) or (not channel.cached_permissions_for(client).can_add_reactions):
            return
        
        message.weakrefer()
        
        for emoji in self.EMOJIS:
            await client.reaction_add(message,emoji)

        self.timeouter=Timeouter(client.loop,self,timeout=300.)
        client.events.reaction_add.append(self,message)
        client.events.reaction_delete.append(self,message)
        
        return self
    
    async def __call__(self,client,emoji,user):
        if user.is_bot or (emoji not in self.EMOJIS):
            return
        
        message=self.message
        can_manage_messages=self.channel.cached_permissions_for(client).can_manage_messages

        if can_manage_messages:
            if not message.did_react(emoji,user):
                return
            Task(self.reaction_remove(client,message,emoji,user),client.loop)

        if self.task_flag:
            return
        
        while True:
            if emoji is self.CYCLE:
                url=pop_one(self.urls) if self.pop else choose_notsame(self.urls,message.embeds[0].image.url)
                self.history.append(url)
                self.history_step=1
                break
            
            if emoji is self.BACK:
                history=self.history
                history_ln=len(history)
                if history_ln<2:
                    return
                
                history_step=self.history_step
                if history_step==history_ln:
                    history_step=0
                
                history_step=history_step+1
                self.history_step=history_step
                url=history[history_ln-history_step]
                break
                
            return
        
        embed=Embed(self.title,color=BOORU_COLOR,url=url)
        embed.add_image(url)
        
        self.task_flag=GUI_STATE_SWITCHING_PAGE
        try:
            await client.message_edit(message,embed=embed)
        except DiscordException:
            self.task_flag=GUI_STATE_CANCELLED
            self.cancel()
            return
            
        if not self.urls:
            self.task_flag=GUI_STATE_CANCELLED
            self.cancel()
            return
        
        self.task_flag=GUI_STATE_READY

        self.timeouter.timeout+=20.0
            
    @staticmethod
    async def reaction_remove(client,message,emoji,user):
        try:
            await client.reaction_delete(message,emoji,user)
        except DiscordException:
            pass

    async def _canceller(self,exception):
        client=self.client
        message=self.message
        
        client.events.reaction_add.remove(self,message)
        client.events.reaction_delete.remove(self,message)

        if self.task_flag==GUI_STATE_SWITCHING_CTX:
            # the message is not our, we should not do anything with it.
            return
        
        self.task_flag=GUI_STATE_CANCELLED
        
        if exception is None:
            return
        
        if isinstance(exception,TimeoutError):
            if self.channel.cached_permissions_for(client).can_manage_messages:
                try:
                    await client.reaction_clear(message)
                except DiscordException:
                    pass
            
            return
        
        timeouter=self.timeouter
        if timeouter is not None:
            timeouter.cancel()
        #we do nothing
    
    def cancel(self):
        canceller=self.canceller
        if canceller is None:
            return
        
        self.canceller=None
        
        timeouter=self.timeouter
        if timeouter is not None:
            timeouter.cancel()
        
        return Task(canceller(self,None),self.client.loop)
        
async def answer_booru(client,channel,content,url_base):
    if content:
        content=content.split()
        content.insert(0,url_base)
        url='+'.join(content)
    else:
        url=url_base
    
    async with client.http.request_get(url) as response:
        result = await response.read()
    if response.status!=200:
        await client.message_create(channel,
            embed=Embed('Booru is unavailable',color=BOORU_COLOR))
        return
    
    soup=BeautifulSoup(result,'lxml')
    urls=[post['file_url'] for post in soup.find_all('post')]
    if urls:
        await ShuffledShelter(client,channel,urls,True)
        return
    
    await client.message_create(channel,embed=Embed(
        f'Sowwy, but {client.name} could not find anything what matches these tags..',
        color=BOORU_COLOR))

@booru_commands
@Cooldown('channel',20.,limit=2,handler=CooldownHandler())
@mark_as_async
def safebooru(client,message,content):
    return answer_booru(client,message.channel,content,SAFE_BOORU)

async def _help_safebooru(client,message):
    prefix=client.events.message_create.prefix(message)
    embed=Embed('safebooru',(
        'Do you want me, to request some images from safebooru?\n'
        f'Usage: `{prefix}safebooru *tags*`\n'
        'You should pass at least 1 tag.'
        ),color=KOISHI_HELP_COLOR)
    await client.message_create(message.channel,embed=embed)

KOISHI_HELPER.add('safebooru',_help_safebooru)

class nsfw_checker():
    __slots__=('command',)
    __async_call__=True
    
    def __init__(self,command):
        self.command=command
    
    def __call__(self,client,message,content):
        if getattr(message.channel,'nsfw',False):
            return self.command(client,message,content)
        
        if re.search(client.name,content,re.I) is None:
            text='Onii chaan\~,\nthis is not the right place to lewd.'
        else:
            text='I love you too\~,\nbut this is not the right place to lewd.'
        
        return client.message_create(message.channel,embed=Embed(
            text,color=BOORU_COLOR))

    @property
    def __name__(self):
        return self.command.__name__

@booru_commands
@nsfw_checker
@safebooru.shared()
@mark_as_async
def nsfwbooru(client,message,content):
    return answer_booru(client,message.channel,content,NSFW_BOORU)

async def _help_nsfwbooru(client,message):
    prefix=client.events.message_create.prefix(message)
    embed=Embed('nsfwbooru',(
        'Do you want me, to request some images from gelbooru?... You perv!\n'
        f'Usage: `{prefix}nsfwbooru *tags*`\n'
        'You should pass at least 1 tag. '
        'Passing nsfw tags is recommended as well.'
            ),color=KOISHI_HELP_COLOR).add_footer(
            'NSFW channel only!')
    await client.message_create(message.channel,embed=embed)

KOISHI_HELPER.add('nsfwbooru',_help_nsfwbooru)

for title,tag_name,command_names in (
        ('Aki Minoriko',            'aki_minoriko',         ('minoriko',),),
        ('Aki Shizuha',             'aki_shizuha',          ('shizuha',),),
        ('Chairudo Runa',           'luna_child',           ('runa','luna',),),
        ('Chen',                    'chen',                 ('chen',),),
        ('Chiruno',                 'cirno',                ('chiruno','cirno',),),
        ('Daiyousei',               'daiyousei',            ('daiyousei',),),
        ('Ebisu Eika',              'ebisu_eika',           ('eika',),),
        ('Erii',                    'elly',                 ('erii','elly',),),
        ('Etanitiraruba',           'eternity_larva',       ('eternity','Etanitiraruba',),),
        ('Fujiwara no Mokou',       'fujiwara_no_mokou',    ('mokou',),),
        ('Futatsuiwa Mamizou',      'futatsuiwa_mamizou',   ('mamizou',),),
        ('Haan Maeriberii',         'maribel_hearn',        ('maeriberii','maribel',),),
        ('Haniyasushin Keiki',      'haniyasushin_keiki',   ('keiki',),),
        ('Hakurei Reimu',           'hakurei_reimu',        ('reimu',),),
        ('Hata no Kokoro',          'hata_no_kokoro',       ('kokoro',),),
        ('Hei Meirin',              'hei_meiling',          ('hei',),),
        ('Hieda no Akyuu',          'hieda_no_akyuu',       ('akyuu',),),
        ('Hijiri Byakuren',         'hijiri_byakuren',      ('byakuren',),),
        ('Himekaidou Hatate',       'himekaidou_hatate',    ('hatate',),),
        ('Hinanawi Tenshi',         'hinanawi_tenshi',      ('tenshi',),),
        ('Hon Meirin',              'hong_meiling',         ('meirin','meiling','hong',),),
        ('Horikawa Raiko',          'horikawa_raiko',       ('raiko',),),
        ('Hoshiguma Yuugi',         'hoshiguma_yuugi',      ('yuugi',),),
        ('Houjuu Nue',              'houjuu_nue',           ('nue',),),
        ('Houraisan Kaguya',        'houraisan_kaguya',     ('kaguya',),),
        ('Howaito Ririi',           'lily_white',           ('ririi','lily',),),
        ('Howaitorokku Retii',      'letty_whiterock',      ('retii','letty',),),
        ('Ibaraki Kasen',           'ibaraki_kasen',        ('kasen',),),
        ('Ibuki Suika',             'ibuki_suika',          ('suika',),),
        ('Imaizumi Kagerou',        'imaizumi_kagerou',     ('kagerou',),),
        ('Inaba Tewi',              'inaba_tewi',           ('tewi',),),
        ('Inubashiri Momiji',       'inubashiri_momiji',    ('momiji',),),
        ('Izayoi Sakuya',           'izayoi_sakuya',        ('sakuya',),),
        ('Joutouguu Mayumi',        'joutougu_mayumi',      ('mayumi',),),
        ('Junko',                   'junko_(touhou)',       ('junko',),),
        ('Kaenbyou Rin',            'kaenbyou_rin',         ('rin',),),
        ('Kagiyama Hina',           'kagiyama_hina',        ('hina',),),
        ('Kaku Seiga',              'kaku_seiga',           ('seiga',),),
        ('Kamishirasawa Keine',     'kamishirasawa_keine',  ('keine',),),
        ('Kasodani Kyouko',         'kasodani_kyouko',      ('kyouko',),),
        ('Kawashiro Nitori',        'kawashiro_nitori',     ('nitori',),),
        ('Kazami Yuuka',            'kazami_yuuka',         ('yuuka',),), # same as 'kazami_youka'
        ('Kicchou Yachie',          'kitcho_yachie',        ('yachie',),),
        ('Kijin Seija',             'kijin_seija',          ('seija',),),
        ('Kirisame Marisa',         'kirisame_marisa',      ('marisa',),),
        ('Kishin Sagume',           'kishin_sagume',        ('sagume',),),
        ('Kisume',                  'kisume',               ('kisume',),),
        ('Kitashirakawa Chiyuri',   'kitashirakawa_chiyuri',('chiyuri',),),
        ('Koakuma',                 'koakuma',              ('koakuma',),),
        ('Kochiya Sanae',           'kochiya_sanae',        ('sanae',),),
        ('Komano Aunn',             'komano_aun',           ('aunn','aun',),),
        ('Komeiji Koishi',          'komeiji_koishi',       ('koishi',),),
        ('Komeiji Satori',          'komeiji_satori',       ('satori',),),
        ('Konngara',                'konngara',             ('konngara',),),
        ('Konpaku Youmu',           'konpaku_youmu',        ('youmu',),),
        ('Kokuu Haruto',            'kokuu_haruto',         ('kokuu',),), # no result now
        ('Kuraunpiisu',             'clownpiece',           ('kuraunpiisu','clownpiece',),),
        ('Kurodani Yamame',         'kurodani_yamame',      ('yamame',),),
        ('Kurokoma Saki',           'kurokoma_saki',        ('saki',),),
        ('Maagatoroido Arisu',      'alice_margatroid',     ('arisu','alice',),),
        ('Matara Okina',            'matara_okina',         ('okina',),),
        ('Merankorii Medisun',      'medicine_melancholy',  ('medisun', 'medicine',),),
        ('Mima',                    'mima',                 ('mima',),),
        ('Sanii Miruku',            'sunny_milk',           ('sanii','sunny',),),
        ('Miyako Yoshika',          'miyako_yoshika',       ('yoshika',),),
        ('Mizuhashi Parusi',        'mizuhashi_parsee',     ('parusi','parsee',),),
        ('Mononobe no Futo',        'mononobe_no_futo',     ('futo',),),
        ('Morichika Rinnosuke',     'morichika_rinnosuke',  ('rinnosuke',),),
        ('Moriya Suwako',           'moriya_suwako',        ('suwako',),),
        ('Motoori Kosuzu',          'motoori_kosuzu',       ('kosuzu',),),
        ('Murasa Minamitsu',        'murasa_minamitsu',     ('minamitsu',),),
        ('Nagae Iku',               'nagae_iku',            ('iku',),),
        ('Nazuurin',                'nazrin',               ('nazuurin','nazrin',),),
        ('Nishida Satono',          'nishida_satono',       ('satono',),),
        ('Niwatari Kutaka',         'niwatari_kutaka',      ('kutaka',),),
        ('Onozuka Komachi',         'onozuka_komachi',      ('komachi',),),
        ('Pachurii Noorejji',       'patchouli_knowledge',  ('patchouli',),),
        ('Purizumuribaa Meruran',   'merlin_prismriver',    ('meruran','merlin',),),
        ('Purizumuribaa Ririka',    'lyrica_prismriver',    ('ririka','lyrica',),),
        ('Purizumuribaa Runasa',    'lunasa_prismriver',    ('runasa','lunasa',),),
        ('Rapisurazuri Hekaatia',   'hecatia_lapislazuli',  ('hekaatia','hecatia',),),
        ('Reisen Udongein Inaba',   'reisen_udongein_inaba',('reisen',),),
        ('Reiuji Utsuho',           'reiuji_utsuho',        ('utsuho','okuu',),),
        ('Riguru Naitobagu',        'wriggle_nightbug',     ('riguru','wriggle',),),
        ('Ringo',                   'ringo_(touhou)',       ('ringo',),),
        ('Roorerai Misutia',        'mystia_lorelei',       ('misutia','mystia',),),
        ('Ruumia',                  'rumia',                ('ruumia','rumia',),),
        ('Safaia Sutaa',            'star_sapphire',        ('sutaa','star',),),
        ('Saigyouji Yuyuko',        'saigyouji_yuyuko',     ('yuyuko',),),
        ('Saigyouji Yuyuko',        'saigyouji_yuyuko',     ('yuyuko',),),
        ('Sakata Nemuno',           'sakata_nemuno',        ('nemuno',),),
        ('Seiran',                  'seiran_(touhou)',      ('seiran',),),
        ('Sekibanki',               'sekibanki',            ('sekibanki',),),
        ('Shameimaru Aya',          'shameimaru_aya',       ('aya',),),
        ('Shiki Eiki Yamazanadu',   'shiki_eiki',           ('eiki',),),
        ('Suiito Doremii',          'doremy_sweet',         ('doremy',),),
        ('Sukaaretto Furandooru',   'flandre_scarlet',      ('furandooru','flandre',),),
        ('Sukaaretto Remiria',      'remilia_scarlet',      ('remiria','remilia',),),
        ('Sukuna Shinmyoumaru',     'sukuna_shinmyoumaru',  ('sukuna',),),
        ('Tatara Kogasa',           'tatara_kogasa',        ('kogasa',),),
        ('Teireida Mai',            'teireida_mai',         ('mai',),),
        ('Toramaru Shou',           'toramaru_shou',        ('shou',),),
        ('Toyosatomimi no Miko',    'toyosatomimi_no_miko', ('miko',),),
        ('Usami Renko',             'usami_renko',          ('renko',),),
        ('Usami Sumireko',          'usami_sumireko',       ('sumireko',),),
        ('Ushizaki Urumi',          'ushizaki_urumi',       ('urumi',),),
        ('Wakasagihime',            'wakasagihime',         ('wakasagi','wakasagihime',),),
        ('Watatsuki no Toyohime',   'watatsuki_no_toyohime',('toyohime',),),
        ('Watatsuki no Yorihime',   'watatsuki_no_yorihime',('yorihime',),),
        ('Yagokoro Eirin',          'yagokoro_eirin',       ('eirin',),),
        ('Yakumo Ran',              'yakumo_ran',           ('ran',),),
        ('Yakumo Yukari',           'yakumo_yukari',        ('yukari',),),
        ('Yasaka Kanako',           'yasaka_kanako',        ('kanako',),),
        ('Yatadera Narumi',         'yatadera_narumi',      ('narumi',),),
        ('Yorigami Joon',           'yorigami_jo\'on',      ('joon',),),
        ('Yorigami Shion',          'yorigami_shion',       ('shion',),),
            ):
    command=cached_booru_command(title,tag_name)
    for command_name in command_names:
        booru_commands(command,case=command_name)

del title, tag_name, command_names, command, command_name
del Color, BUILTIN_EMOJIS, Cooldown, CooldownHandler, mark_as_async, eventlist
