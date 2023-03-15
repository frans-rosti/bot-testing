import os
import discord
from discord.ext import commands
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

# optin allows players to join the game. automatically checks the database for the user
@bot.command()
async def optin(ctx):
    author = ctx.message.author
    author_id = str(author.id)

    cursor = savedata.cursor()

    query = '''
        SELECT user_id, status FROM players WHERE user_id = ?
    '''
    cursor.execute(query, (author_id,))

    name_status = cursor.fetchall()

    if not name_status:
        starting_cash = 1000
        starting_rep = 0
        savedata.execute('INSERT INTO econ_stats (user_id, balance) VALUES (?, ?)', (author_id, starting_cash))
        savedata.execute('INSERT INTO rep_stats (user_id, reputation) VALUES (?, ?)', (author_id, starting_rep))
        savedata.execute('INSERT INTO players (user_id, status) VALUES (?, ?)', (author_id, "in"))
        savedata.commit()
        print(f'User was added:\nUsername: {author}\nID: {author_id}')
        await ctx.send(f'Welcome to the System! Your complementary coins have been automatically deposited to your account.\nYou can check your balance at any time with the "econ.balance" command.')

    elif name_status and name_status[0][1] == "out":
        return_cash = 500
        return_rep = -10
        savedata.execute('INSERT INTO econ_stats (user_id, balance) VALUES (?, ?)', (author_id, return_cash))
        savedata.execute('INSERT INTO rep_stats (user_id, reputation) VALUES (?, ?)', (author_id, return_rep))
        cursor.execute("UPDATE players SET status = ? WHERE user_id = ?", ('in', author_id))
        savedata.commit()
        await ctx.send('Welcome back! The System missed you. You have been given some coins to welcome your return.')

    elif name_status and name_status[0][1] == "in":
        await ctx.send('You are already in.')

# allows the user to check the database for their current coin balance
@bot.command()
async def balance(ctx):
    author = ctx.message.author
    author_id = str(author.id)

    cursor = savedata.cursor()
    cursor.execute("SELECT balance FROM econ_stats WHERE user_id=?", (author_id,))
    coins = cursor.fetchone()

    if coins:
        balance = coins[0]
        await ctx.send(f'Your balance is: {balance} Coins.')
        print(f'Balance check: {author} = {balance}.')
    else:
        await ctx.send("It seems you haven't opted in just yet. You can do this with the 'econ.optin' command.")
        print("Balance check denied, player has not opted in.")

# opts the player out of the game. the player cannot participate, until they opt in again
@bot.command()
async def optout(ctx):
    author = ctx.message.author
    author_id = str(author.id)

    cursor = savedata.cursor()
    cursor.execute("SELECT user_id FROM players WHERE user_id=?", (author_id,))
    name_check = cursor.fetchone()

    if name_check is None:
        await ctx.send("You can't opt out, you haven't even started! Use 'econ.optin' to start playing.")
    else:
        print(f'Opt out request:\nUser: {author}\nID: {author_id}')
        cursor.execute("DELETE FROM econ_stats WHERE user_id=?", (author_id,))
        cursor.execute("DELETE FROM rep_stats WHERE user_id=?", (author_id,))
        cursor.execute("UPDATE players SET status = ? WHERE user_id = ?", ('out', author_id))
        savedata.commit()
        print(f'User removed.')
        await ctx.send("Sorry to see you go. You can start playing again at any time with the econ.optin command. Your game data has been deleted.")

# trading - allows users to trade coins amongst each other
@bot.command()
async def trade(ctx, username, amount: int):
    sender = ctx.message.author
    sender_id = str(sender.id)
    receiver = discord.utils.get(client.users, name=username)
    receiver_id = str(receiver.id)
    cursor = savedata.cursor()
    cursor.execute("SELECT balance FROM econ_stats WHERE user_id=?", (sender_id,))
    sender_coins = cursor.fetchone()

    if receiver is None:
        await ctx.send("No user found with this username. Try again.")
    elif amount > sender_coins[0]:
        await ctx.send("You don't have enough coins to complete this request.")
    else:
        await ctx.send("Trade request received. Please wait.")
        print(f'Trade request, {sender} ({sender.id}) to {receiver} ({receiver.id})')
        new_balance_sender = int(sender_coins[0])-amount
        cursor.execute("UPDATE econ_stats SET balance = ? WHERE user_id =?", (new_balance_sender, sender_id))
        cursor.execute("SELECT balance FROM econ_stats WHERE user_id = ?", (receiver_id,))
        receiver_coins = cursor.fetchone()
        new_balance_receiver = int(receiver_coins[0]) + amount
        cursor.execute("UPDATE econ_stats SET balance = ? WHERE user_id = ?", (new_balance_receiver, receiver_id))
        await ctx.send(f"Trade successful! {sender}, your new balance is {new_balance_sender}.\n{receiver}, your new balance is {new_balance_receiver}.")
        print(f"Trade complete. From {sender} to {receiver}, {amount} Coins.\n{sender_id} balance = {new_balance_sender}\n{receiver_id} balance = {new_balance_receiver}")

        





# command used to delete all the user data of a specified player
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
            cursor.execute("DELETE FROM econ_stats WHERE user_id=?", (user_id,))
            cursor.execute("DELETE FROM rep_stats WHERE user_id=?", (user_id,))
            cursor.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
            savedata.commit()
            print(f"The complete data for user: {user_id} was deleted.")
            await ctx.send("Removal request complete. All user data and history has been removed.")

        else:
            await ctx.send("You don't have the required permissions for this command. Get in touch with the administrators for further assistance.")

bot.run(TOKEN)

