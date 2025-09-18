#!/usr/bin/env python3
"""
Simple Discord connection test
"""

import os
import asyncio
import discord
from discord.ext import commands

async def test_connection():
    """Test basic Discord connection"""
    token = os.getenv('DISCORD_TOKEN')
    channel_id = int(os.getenv('DISCORD_CHANNEL_ID', '1405408713505771652'))
    
    print(f"Token: {token[:20]}...")
    print(f"Channel ID: {channel_id}")
    
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'Bot connected as {bot.user}')
        print(f'Bot ID: {bot.user.id}')
        
        # Test channel access
        channel = bot.get_channel(channel_id)
        if channel:
            print(f'Channel found: {channel.name} ({channel.id})')
            print(f'Channel type: {channel.type}')
            print(f'Guild: {channel.guild.name if channel.guild else "None"}')
            
            # Try to get recent messages
            try:
                messages = []
                async for message in channel.history(limit=5):
                    messages.append(message)
                print(f'Found {len(messages)} recent messages')
                
                for i, msg in enumerate(messages):
                    print(f'  {i+1}. {msg.author.name}: {msg.content[:50]}...')
                    
            except Exception as e:
                print(f'Error reading messages: {e}')
        else:
            print(f'Channel {channel_id} not found')
            print('Available channels:')
            for guild in bot.guilds:
                print(f'  Guild: {guild.name}')
                for ch in guild.channels:
                    if hasattr(ch, 'name'):
                        print(f'    - {ch.name} ({ch.id})')
        
        await bot.close()
    
    try:
        await bot.start(token)
    except Exception as e:
        print(f'Connection error: {e}')

if __name__ == "__main__":
    asyncio.run(test_connection())
