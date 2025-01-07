
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

#Creating an intent object. Setting the events the bot is allowed to listen to. Automatically setting to default
intents = discord.Intents.default()
#Allowing bot to listen to message events, and server related events
intents.messages = True
intents.guilds = True
intents.message_content = True

#Initializing the bots commands, so that it can be summoned with the !, or automatically respond to events based on the intent settings
trade_bot = commands.Bot(command_prefix = "!", intents = intents)

@trade_bot.event
async def on_ready():
    """
    Function that automatically runs when the bot is connected and opened. 
    Output: Prints that the bot is connected
    """
    print(f"{trade_bot.user.name} is connected to Discord!")
    await trade_bot.change_presence(activity=discord.Game(name="Managing Trades"))

    if not update_prices.is_running():
        update_prices.start()

    track_price_changes.start()

def item_prices():
    krunker_market_url = "https://krunker.io/social.html?p=market"
    #Options is a class which allows custom configuration of chrome browser
    options = Options()
    #Allows Selenium to run browser in headless mode, where dont need GUI
    options.headless = True
    #Creates new Chrome WebDriver instance with option as a configuration object. 
    #Helps automate browser and interact with Chrome
    chrome_driver = webdriver.Chrome(options = options)
    #Browser navigates to krunker market url and scrapes
    chrome_driver.get(krunker_market_url)
    #Webdriver waits 10 seconds for elements to show on page before returning an error
    chrome_driver.implicitly_wait(10)

    #Locates elements on page with class name of cardAction, then returns list of matching elements. 
    #First argument in find elements means locating elements on webpage based on HTML class attribute
    #Second argument refers to the specific class needed
    market_cards = chrome_driver.find_elements(By.CLASS_NAME, "cardAction")
    cosmetic_items = {}

    #Breakpoint #1
    print("Extracting item IDs and prices:")

    #Finds all HTML elements in market cards list, where each HTML element represents a certain tag
    for cosmetics in market_cards:
        #onclick attribuate contains JavaScript code which contains arguments for the cosmetic item
        onclick_attribute = cosmetics.get_attribute("onclick")
        if onclick_attribute:
            parms = onclick_attribute.split(",")
            if len(parms) >= 6:
                #Obtains item attributes through indexing/patterns, and strips the "" to get just the values
                item_id = parms[4].strip('"') 
                price_tag = parms[5].strip('"') 
                img_url = parms[2].strip('"')

                #Breakpoint #2
                print(f"Extracted ID: {item_id}, Price: {price_tag}")
                
                item = {
                'item_id': item_id,
                'price': price_tag,
                'img_url': img_url
            }
                cosmetic_items[item_id] = item
    #Closing browser session hosted by Selenium and frees space that was created by window opened during scraping
    chrome_driver.quit()
    #Breakpoint #3
    print(f"Extracted items: {cosmetic_items}")
    return cosmetic_items

#Initalize a global dictionary 
temp_prices = {}

#Decorator that creates a loop to run periodicly 
@tasks.loop(hours = 1)
async def update_prices():
    """
    Function that performs tasks without blocking program. It updates prices every hour
    Output: Updates prices every hour + prints success message
    """
    #Need global or else would create local temp prices
    global temp_prices
    #Breakpoint #4
    print("Starting price update...")
    temp_prices = item_prices()
    if temp_prices:
        print("Prices successfully updated!")
    else:
        print("No prices were extracted.")

@trade_bot.command()
async def single_item_price(ctx, *, item_id):
    """
    Async function that takes finds the price of a specific item
    Input: Takes ctx which is automatically passed by the bot when command called. 
    Input: Takes item name from user when command used. The * means will capture everything after command as a single argument. Helpful for items with spaces in bewteen
    """
    #Breakpoint #5
    print(f"Received item_id: {item_id}")
    #Breakpoint #6
    print(f"Current temp_prices: {temp_prices}")

    if not temp_prices:
        await ctx.send("Prices are not available yet. Please try again after a few minutes.")
        return
    
    #Searches temp price dictionary for item id provided by user. If not found, returns an error message
    price = temp_prices.get(item_id, "Item not found")
    #Breakpoint #7
    print(f"Searching for {item_id} in prices... Found: {price}")
    #ctx.send sends message back to channel where command was used. Await used in async to wait for message to be sent before continuing
    await ctx.send(f"Price for {item_id} : {price}")

@trade_bot.command()
async def item_trade(ctx, *, item_name):
    #ctx.author refers to the user who sent the command, and returns their trade request to the same channel
    await ctx.send(f"{ctx.author} is offering {item_name}. React if you want to trade!")

previous_prices = {}

#Setting task time to recur every 10 minutes
@tasks.loop(minutes = 10)
async def track_price_changes():
    global previous_prices, temp_prices
    new_prices = item_prices()
    
    #Looping through new prices dictionary, creating tuple with key being items and value being new_price
    for item, new_price in new_prices.items():
        new_price = new_price.get("price")
        #Setting old price to the value of the item obtaned from previous prices dictionary
        old_price = previous_prices.get(item, {}).get("price")
        if old_price is not None and old_price != new_price:
            #Sending updated price notifcations if prices changed, to the specified channel in the server with a message (Trade-Chat)
            channel = trade_bot.get_channel(913942251837751316)
            channel = await channel.send (f"Price update: {item} is now {new_price}. Old Price was {old_price}")
    previous_prices = new_prices

@trade_bot.command()
async def schedule_event(ctx, date, time, *, description):
    #Converts string into datetime object based on year, month, date, time formatting. (String Parse Time)
    event_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    await ctx.send(f"Event scheduled for {date} at {time}: {description}")

    #Computes the reminder time by subtracting 1 hour from the event time (gets an actual time)
    reminder_time = event_time - timedelta(hours = 1)
    #Checks when the current time is less than the reminder time
    while datetime.now() < reminder_time:
        #Does the check every 1 minute, as doing it constantly can slow performance
        await asyncio.sleep(60)
    #Once while fails, will send the reminder immediately
    await ctx.send(f"Reminder: The event '{description}' starts in 1 hour!")

#Triggers on_message event everytime a message is sent in text channels
@trade_bot.event
async def on_message(message):

    #Ignores message sent by bot itself
    if message.author == trade_bot.user:
        return
    
    banned_words = [
    "f***", "sh*t", "d***", "a**", "b****", "c***", "n****", "f****t", "tr***y", 
    "k***", "ch***", "sp***", "noob", "trash", "loser", "idiot", "you suck", "die", 
    "kill yourself", "hook up", "aimbot", 
    "wallhack", "free skins", "cheat", "mod menu", "hack"
]   
    #Checks if each word in the banned words list during each iteration is a substring of the entire lowercase phrase. Using if any to see any banned words in phrase
    if any(word in message.content.lower() for word in banned_words):
        await message.delete()
        await message.channel.send(f"{message.author}, please follow the rules!")
    
    await trade_bot.process_commands(message)

@trade_bot.command()
async def hello(ctx):
    print("Hello command triggered")
    await ctx.send(f"Hello! 👋 {ctx.author}")

@trade_bot.command()
async def custom_help(ctx):
    print("Help command triggered")
    await ctx.send("Here's what I can do:\n1. Say hello with `!hello`.\n2. More commands coming soon!")

@trade_bot.event
async def on_command_error(ctx, error):
    #Python function to check if object is an instance of specific class (First argument object checking, and second is class checking against)
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, that command doesn't exist.")

#Bot token code to allow it to start and run
trade_bot.run("FakeTokenCode")
