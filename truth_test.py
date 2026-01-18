import tweepy

# PASTE THE NEW KEYS DIRECTLY BETWEEN THE QUOTES
# DO NOT USE OS.GETENV
api_key = "mgSVudYpFxhgSvRf5uuLb5eag"
api_secret = "9ko9j0rPwGm99FWa3TIe09TsRuOahDD8QnKWDLHbna2FLNW5Be"
access_token = "2012611893857271808-sDpIqduXPeWADJp3R33zACls91nqlN"
access_secret = "vwcfGCYjwJ2UoGhfv8CbzJ5XlMh7QjByBrAOkbkL0qegd"

client = tweepy.Client(
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_secret
)

print("Attempting to post...")
response = client.create_tweet(text="This is the Truth Serum test. Titan Vanguard check.")
print(f"Posted! ID: {response.data['id']}")
