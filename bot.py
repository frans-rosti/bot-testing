import os
import discord
from discord.ext import commands
from discord.utils import get
import configparser
import asyncio
import sqlite3

# sets up the use of a config.ini file to store some bits of information
config = configparser.ConfigParser()
config.read('config.ini')
TOKEN = config.get('keys', 'token')

# game save-data is kept in an sqlite file
savedata = sqlite3.connect('savedata.db')

# sets up the bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='econ.', intents=intents)

# successful bot log in check
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}.')

# test command to check responsiveness
@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')

# check for the required tables in the database
with savedata:
    savedata.execute('''CREATE TABLE IF NOT EXISTS players (user_id TEXT PRIMARY KEY, status TEXT)''')
    savedata.execute('''CREATE TABLE IF NOT EXISTS econ_stats (user_id TEXT PRIMARY KEY, balance TEXT)''')
    savedata.execute('''CREATE TABLE IF NOT EXISTS rep_stats (user_id TEXT PRIMARY KEY, reputation TEXT)''')
    savedata.execute('''CREATE TABLE IF NOT EXISTS system (stat TEXT PRIMARY KEY, stat_value TEXT)''')

# used to start the game on a server.
@bot.command()
async def start_game(ctx):
    author = ctx.message.author
    author_id = str(author.id)
    section = 'admins'

    for key, value in config.items(section):
        if str(value) == author_id:
            if await game_status() == False:
                print('System initialized')
                savedata.execute('''CREATE TABLE IF NOT EXISTS system (stat TEXT PRIMARY KEY, stat_value TEXT)''')
                savedata.execute('INSERT INTO system (stat, stat_value) VALUES (?, ?)', ('system_status', 1))
                savedata.execute('INSERT INTO system (stat, stat_value) VALUES (?, ?)', ('system_balance', 1000000))
                savedata.execute('INSERT INTO system (stat, stat_value) VALUES (?, ?)', ('system_productivity', 100))
                savedata.execute('INSERT INTO system (stat, stat_value) VALUES (?, ?)', ('system_level', 1))
                savedata.execute('INSERT INTO system (stat, stat_value) VALUES (?, ?)', ('system_experience', 1))
                savedata.execute('INSERT INTO system (stat, stat_value) VALUES (?, ?)', ('system_player_count', 0))
                savedata.commit()
                system_status = 1
            else: 
                await ctx.send("Game is already running.")
        else:
            await ctx.send("You don't have the required permissions for this command. Get in touch with the administrators for further assistance.")

# used to check all system stats
@bot.command()
async def system_status(ctx):
    cursor = savedata.cursor()
    cursor.execute('SELECT * FROM system')
    rows = cursor.fetchall()
    for row in rows:
        await ctx.send(f'{row}')


# used to check if the game has been started
async def game_status():
    cursor = savedata.cursor()
    cursor.execute("SELECT stat_value FROM system WHERE stat = ?", ('system_status',))
    game_status_check = cursor.fetchone()

    if game_status_check and game_status_check[0] == '1':
        game_status = True
    else:
        game_status = False
    
    return game_status

# balance check function
async def balance_check(player):
    cursor = savedata.cursor()
    cursor.execute("SELECT balance FROM econ_stats WHERE user_id=?", (player,))
    balance = cursor.fetchone()
    if balance:
        return balance[0]
    else:
        return False

# check user status
async def status_check(player):
    cursor = savedata.cursor()
    cursor.execute("SELECT status FROM players WHERE user_id=?", (player,))
    status = cursor.fetchone()

    if not status:
        status_check = 'fail'
    elif status and status[0] == 'out':
        status_check = 'out'
    else: 
        status_check = 'in'

    return status_check

# add one to the player count
async def add_player():
    cursor = savedata.cursor()
    cursor.execute('SELECT stat_value FROM system WHERE stat = ?', ('system_player_count',))
    player_count = int(cursor.fetchone()[0]) + 1
    cursor.execute('UPDATE system SET stat_value = ? WHERE stat = ?', (player_count, 'system_player_count'))
    print(f'Player count = {player_count}.')

# remove one player from the count
async def remove_player():
    cursor = savedata.cursor()
    cursor.execute('SELECT stat_value FROM system WHERE stat = ?', ('system_player_count',))
    player_count = int(cursor.fetchone()[0]) - 1
    cursor.execute('UPDATE system SET stat_value = ? WHERE stat = ?', (player_count, 'system_player_count'))
    print(f'Player count = {player_count}.')

# check the system level
async def system_level_check():
    cursor = savedata.cursor()
    cursor.execute('SELECT stat_value FROM system WHERE stat = ?', ('system_level'))
    system_level = int(cursor.fetchone()[0])
    return system_level

# check system experience
async def system_experience_check():
    cursor = savedata.cursor()
    cursor.execute('SELECT stat_value FROM system WHERE stat = ?', ('system_experience'))
    system_experience = int(cursor.fetchone()[0])
    return system_experience

# check system balance
async def system_balance_check():
    cursor = savedata.cursor()
    cursor.execute('SELECT stat_value FROM system WHERE stat = ?', ('system_balance'))
    system_balance = int(cursor.fetchone()[0])
    return system_balance

# check system productivity
async def system_productivity_check():
    cursor = savedata.cursor()
    cursor.execute('SELECT stat_value FROM system WHERE stat = ?', ('system_productivity'))
    system_productivity = int(cursor.fetchone()[0])
    return system_productivity

# check system player count
async def system_player_count_check():
    cursor = savedata.cursor()
    cursor.execute('SELECT stat_value FROM system WHERE stat = ?', ('system_player_count'))
    system_player_count = int(cursor.fetchone()[0])
    return system_player_count

# optin allows players to join the game. automatically checks the database for the user
@bot.command()
async def optin(ctx):
    author = ctx.message.author
    author_id = str(author.id)
    cursor = savedata.cursor()

    player_status = await status_check(author_id)

    if player_status == 'fail':
        starting_cash = 1000
        starting_rep = 0
        savedata.execute('INSERT INTO econ_stats (user_id, balance) VALUES (?, ?)', (author_id, starting_cash))
        savedata.execute('INSERT INTO rep_stats (user_id, reputation) VALUES (?, ?)', (author_id, starting_rep))
        savedata.execute('INSERT INTO players (user_id, status) VALUES (?, ?)', (author_id, "in"))
        await add_player()
        savedata.commit()
        print(f'User was added:\nUsername: {author}\nID: {author_id}')
        await ctx.send(f'Welcome to the System! Your complementary coins have been automatically deposited to your account.\nYou can check your balance at any time with the "econ.balance" command.')

    elif player_status == 'out':
        return_cash = 500
        return_rep = -10
        savedata.execute('INSERT INTO econ_stats (user_id, balance) VALUES (?, ?)', (author_id, return_cash))
        savedata.execute('INSERT INTO rep_stats (user_id, reputation) VALUES (?, ?)', (author_id, return_rep))
        cursor.execute("UPDATE players SET status = ? WHERE user_id = ?", ('in', author_id))
        await add_player()
        savedata.commit()
        await ctx.send('Welcome back! The System missed you. You have been given some coins to welcome your return.')

    elif player_status == 'in':
        await ctx.send('You are already in.')

# allows the user to check the database for their current coin balance
@bot.command()
async def balance(ctx):
    author = ctx.message.author
    author_id = str(author.id)

    player_status = await status_check(author_id)

    if player_status == 'in':
        player_balance = await balance_check(author_id)
        await ctx.send(f'Your balance is: {player_balance} Coins.')
        print(f'Balance check: {author} = {player_balance}.')
    else:
        await ctx.send("It seems you haven't opted in just yet. You can do this with the 'econ.optin' command.")
        print("Balance check denied, player has not opted in.")

# opts the player out of the game. the player cannot participate, until they opt in again
@bot.command()
async def optout(ctx):
    author = ctx.message.author
    author_id = str(author.id)

    cursor = savedata.cursor()
    player_status = await status_check(author_id)

    if player_status == 'fail':
        await ctx.send("You can't opt out, you haven't even started! Use 'econ.optin' to start playing.")
    elif player_status == 'out':
        await ctx.send("You have already opted out.")
    else:
        print(f'Opt out request:\nUser: {author}\nID: {author_id}')
        cursor.execute("DELETE FROM econ_stats WHERE user_id=?", (author_id,))
        cursor.execute("DELETE FROM rep_stats WHERE user_id=?", (author_id,))
        cursor.execute("UPDATE players SET status = ? WHERE user_id = ?", ('out', author_id))
        await remove_player()
        savedata.commit()
        print(f'User removed.')
        await ctx.send("Sorry to see you go. You can start playing again at any time with the econ.optin command. Your game data has been deleted.")

# command used to delete all the user data of a specified player.
@bot.command()
async def deleteeverything(ctx, user_id: int):
    author = ctx.message.author
    author_id = str(author.id)
    section = 'admins'

    cursor = savedata.cursor()
    cursor.execute("SELECT user_id FROM players WHERE user_id=?", (author_id,))
    name_check = cursor.fetchone()

    for key, value in config.items(section):
        if str(value) == author_id:
            cursor.execute("DELETE FROM econ_stats WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM rep_stats WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
            await remove_player()
            savedata.commit()
            print(f"The complete data for user: {user_id} was deleted.")
            await ctx.send("Removal request complete. All user data and history has been removed.")

        else:
            await ctx.send("You don't have the required permissions for this command. Get in touch with the administrators for further assistance.")

bot.run(TOKEN)

