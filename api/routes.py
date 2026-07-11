import os
from fastapi import APIRouter, HTTPException, Query
from bot.client import bot
import discord
from typing import Optional

router = APIRouter()

CHANNEL_KEYS = {
    'rules': 'RULES_CHANNEL_ID',
    'annoucements': 'ANNOUCEMENT_CHANNEL_ID',
    'tech-write': 'TECH_CHANNEL_ID',
    'competition-news': 'COMPETITION_CHANNEL_ID',
    'consumer-news': 'CONSUMER_CHANNEL_ID',
    'admin': 'ADMIN_CHANNEL_ID'
}

@router.post('/setup/{channel_name}')
async def setup_channel_message(channel_name: str, purpose: str = Query(None, description='The structural description text describing why this channel exists.'), general_info: Optional[str] = Query(None, description="Optional extra informational guidelines.")):
    if not bot.is_ready():
        raise HTTPException(status_code=503, detail='Discord connection is initializing. Try again momentarily')
    
    if channel_name.lower() not in CHANNEL_KEYS:
        raise HTTPException(status_code=404, detail='Target text channel not found in server cluster.')
    
    channel_id = int(os.getenv(CHANNEL_KEYS[channel_name]))
    if not channel_id:
        raise HTTPException(status_code=500, detail=f'Target environment config var for {channel_name} missing.')
    
    channel = bot.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        raise HTTPException(status_code=404, detail=f'Target text channel not found in server cluster.')

    embed = discord.Embed(
        title=f'Welcome to {channel_name}',
        description=f'### 📋 Purpose\n{purpose}',
        color=discord.Color.green()
    )

    if general_info:
        embed.add_field(name='ℹ️ General Information', value=general_info, inline=False)

    await channel.send(embed=embed)
    return {
        'status': 'Success',
        'message': f'Setup presentation sent in channel {channel_name}'
        }
    