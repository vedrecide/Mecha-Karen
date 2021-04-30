import asyncio
import discord
from discord.ext import commands
from Utils._events import *
import urllib.parse
import sys
from Utils import Mongo, _mongo
from Utils import Sensitive
from Utils import GW, GW_CONFIGS
from Utils.warn import Warn
import json

class Dashboard(commands.Cog):
    def __init__(self, bot):
        
        if not hasattr(bot, 'GW', None):
            bot.GW = GW.NEW(**GW_CONFIGS)
            ## Make life easier when theres alot of giveaways running
        
        self.bot = bot
        self.host = Sensitive.WEBIP
        self.port = Sensitive.WEBPORT
        self.sender = None
        self.reader = None
        self.client = bot.client
        
        self.running = bot.GW.open_connection(host='https://mechakaren.xyz/giveaways/%REGEX;".............."%')
        ## PORT is random so dont need to define one as of now

    @property
    def has_emitted(self, ctx):
        raw = self.running.fetch(ctx.guild.id).decode('utf-8', errors='ignore')
        
        if not raw:
            return False
        return json.loads(raw)
    
    async def _read(self, _reader, _writer):
        encoded_data = await _reader.readuntil(b'\n')   ## reads all the data till it finds the escape char \n
        peer_network = _writer.get_extra_info('peername')

        if not peer_network == self.host:
            return False

        decoded_data = encoded_data.decode()

        return decoded_data

    @commands.Cog.listener()
    async def on_ready(self):
        _writer, _reader = await asyncio.open_connection(self.host, self.port)
        self.sender = _writer
        self.reader = _reader
        
        super(Mongo).__init__(self.bot.client, **_mongo)
        
    @commands.Cog.listener()
    async def on_giveaway_start(ctx: commands.Context):
        await self.bot.data_emit(ctx, ctx.code)
        
        if not self.has_emitted(ctx):
            Warn('Failed to send request to %s for giveaway code %s, Using DB version.' % (repr(self.running), ctx.code))
            await self.bot.client.execute('GIVEAWAY', code=ctx.code, file_dict='./cogs/giveaways.py', station_dict='self.giveaways')
        ## ctx.code is nested in the CTX on send
        ## Simple done by
        ## ctx.code = CODE

    @commands.Cog.listener()
    async def on_website_rec(self, data):
        r"""
           Usage:
        --------------
        Data recieved from the websocket is encrypted to prevent packet snatching
        Once a responce has been sent to the website to the bot, if it makes it this event is called.
        Used to read any info which needs to used to modify the bot

        Parameters:
        -----------------
        data: :class:`bytes`
            Encoded instructions / data recieved from the websocket which is connected to the bot
        """
        viable_inst = self._read(data)
        if not viable_inst:
            self.bot.logging.Debug('[{}] | [{}] -> Recieved info from False Peer-Network.', "time", "date")

        _format = Mongo._handle(viable_inst)
        Mongo.execute(_format['data'], mode=_format['mode'])
        
def setup(bot):
    bot.add_cog(Dashboard(bot))
