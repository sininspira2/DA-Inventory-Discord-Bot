import discord
import os
import aiohttp
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

# --- Configuration ---
# Load environment variables from a .env file for local testing
# On Cloud Run, these will be set in the service configuration.
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID") # Optional: For faster command syncing
API_ENDPOINT = "https://api.quotable.io/random" # Example API to call

# A list of role IDs that are allowed to use the command.
ALLOWED_ROLE_IDS = {
    "123456789012345678",
    "987654321098765432"
}

# --- Bot Setup ---
intents = discord.Intents.default()
intents.guilds = True

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced commands to guild: {GUILD_ID}")
        else:
            await self.tree.sync()
            print("Synced commands globally.")

client = MyClient(intents=intents)

# --- Web Server Setup (FastAPI) ---
# This web app will run alongside the bot to keep the Cloud Run instance alive.
app = FastAPI()

@app.get("/")
async def root():
    """Health check endpoint for Google Cloud Run."""
    return {"status": "Bot is alive and listening!"}


@client.event
async def on_ready():
    """Event that fires when the bot is online and ready."""
    print("-" * 20)
    print(f'Logged in as: {client.user} (ID: {client.user.id})')
    print("The bot is now ready to accept commands.")
    print("-" * 20)


# --- Slash Command Definition (No changes needed here) ---
@client.tree.command(name="callapi", description="Calls a web API if the user has the required role.")
async def call_api_command(interaction: discord.Interaction):
    """
    Handles the /callapi slash command.
    Checks user roles and calls an external API.
    """
    user = interaction.user
    user_role_ids = {str(role.id) for role in user.roles}

    if not user_role_ids.intersection(ALLOWED_ROLE_IDS):
        await interaction.response.send_message(
            "Sorry, you don't have the required role to use this command.",
            ephemeral=True
        )
        print(f"Denied access to {user.name} (ID: {user.id}) for /callapi command (missing role).")
        return

    print(f"User {user.name} (ID: {user.id}) has permission. Proceeding with API call.")
    await interaction.response.defer(thinking=True)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_ENDPOINT) as response:
                if response.status == 200:
                    data = await response.json()
                    embed = discord.Embed(
                        title="API Call Successful!",
                        description="Here is a random quote from the API:",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Quote", value=f"_{data.get('content', 'N/A')}_", inline=False)
                    embed.add_field(name="Author", value=f"- {data.get('author', 'Unknown')}", inline=False)
                    embed.set_footer(text="Powered by Quotable API")
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(
                        f"Error: The API returned a status code of `{response.status}`."
                    )
    except aiohttp.ClientError as e:
        print(f"An error occurred during the API call: {e}")
        await interaction.followup.send("An error occurred while trying to connect to the API.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await interaction.followup.send("An unexpected error occurred.")


# --- Main Execution ---
# This part is modified to run both the bot and the web server concurrently.
async def main():
    """Starts the bot and the web server."""
    # Get the port from the environment variable, default to 8080 for local testing
    port = int(os.environ.get("PORT", 8080))
    
    # Configure the Uvicorn server to run the FastAPI app
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)

    # Run the bot and the server concurrently
    # client.start() is the non-blocking version of client.run()
    await asyncio.gather(
        client.start(BOT_TOKEN),
        server.serve()
    )

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN environment variable not found.")
        print("Please create a .env file for local testing or set environment variables in Cloud Run.")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("Shutting down.")

