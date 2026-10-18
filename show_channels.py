"""List connected Buffer channels without saving or printing the API key."""
from getpass import getpass
from auto_post import discover_channels, PostingError
import os

def main():
    key=os.getenv('BUFFER_API_KEY') or getpass('Paste Buffer API key (hidden): ')
    try:
        for c in discover_channels(key):
            print(f"{c.get('service')}: {c.get('displayName') or c.get('name')}  ->  {c['id']}")
    except PostingError as e:
        print('Error:',e)
if __name__ == '__main__': main()
