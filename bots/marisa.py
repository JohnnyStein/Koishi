# -*- coding: utf-8 -*-
from hata import Embed
from hata.ext.commands import setup_ext_commands, checks
from hata.ext.commands.helps.subterranean import SubterraneanHelpCommand
from shared import category_name_rule, DEFAULT_CATEGORY_NAME, MARISA_PREFIX, MARISA_HELP_COLOR, command_error, DUNGEON
from syncer import sync_request_comamnd
from interpreter import Interpreter

setup_ext_commands(Marisa, MARISA_PREFIX, default_category_name=DEFAULT_CATEGORY_NAME,
    category_name_rule=category_name_rule)


Marisa.command_processer.create_category('TEST COMMANDS', checks=[checks.owner_only()])

Marisa.commands(SubterraneanHelpCommand(MARISA_HELP_COLOR), 'help', category='HELP')

Marisa.commands(command_error, checks=[checks.is_guild(DUNGEON)])

async def execute_description(client, message):
    prefix = client.command_processer.get_prefix_for(message)
    return Embed('execute', (
        'Use an interpreter trough me :3\n'
        'Usages:\n'
        f'{prefix}execute #code here\n'
        '*not code*\n'
        '\n'
        f'{prefix}execute\n'
        '# code goes here\n'
        '# code goes here\n'
        '\n'
        f'{prefix}execute\n'
        '```\n'
        '# code goes here\n'
        '# code goes here\n'
        '```\n'
        '*not code*\n'
        '\n'
        '... and many more ways.'
            ), color=MARISA_HELP_COLOR).add_footer(
            'Owner only!')

Marisa.commands(Interpreter(locals().copy()), name='execute', description=execute_description, category='UTILITY',
    checks=[checks.owner_only()])

Marisa.commands(sync_request_comamnd, name='sync', category='UTILITY', checks=[checks.owner_only()])