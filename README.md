## UPDATED FOR DESTINY 2

## Destiny Loadouts
Destiny Loadouts for Amazon Echo's Alexa

Destiny Loadouts lets [Destiny](http://destinythegame.com/) game players easily move items between their Guardians, and between the Vault, by "using their voice" with an Amazon Echo or other Alexa-enabled device.  Destiny Loadouts's goal is to let players transfer items to their guardians quickly, without the use of an external devices such as a phone or a laptop, and without the need to set down their controller.  Destiny Loadouts helps keep the user out of their menus and saves them time by removing the need for them to change characters, fly into a public space where they have access to the vaults, and transfer items.

Destiny Loadouts give players the ability to save a loadout per activity type and per character.  When a loadout is saved it can later be equipped by voice for that character.  In this way if you're waiting in orbit for an activity to start, you can easily equip your ideal weapons and armor for this activity while you wait on your friends to group up.  

Destiny Loadouts also allows you to transfer materials and consumables, and to evenly split them between your characters.  The split consumables option will transfer up to a maximum of a single stack's max size (such as 100 heavy ammo synths) to each character and deposit the remainder in the vault.  You can also transfer by intentional call, such as requesting to get 43 strange coins, pulled from the vault and/or other characters.

Destiny Loadouts is based on the same API service used by the official Destiny Companion app to move and equip items.  Therefore, Destiny Loadouts cannot delete your weapons or armor.  

## Developers
Clone the repo:

* `git clone https://github.com/kissellj/DestinyLoadouts.git`

NOTE: 
  Currently the repo just has the Python code which allows Alexa to interact with your inventory in Destiny 2.  
  There is a lot more to get this to work on your own if you want to clone or fork this project.

  1) You'll need a Bungie API Key to plug into the top of the python code.
      Get your own API key:
      * Goto [Bungie](https://www.bungie.net/en/Application)
      * Copy your API-key from bungie.net into Destiny Loadouts main.py
      
  2) You'll need a place to store the code.  I used AWS Lambda: https://console.aws.amazon.com/lambda cause it made it easy, and it's serverless and free.
  
  3) You'll need a way to query the Bungie Manifest for thinks like their current hash values of items and buckets.  The main.py script shared here does that by querying a PostgreSQL database.  We wanted to avoid download and processing of the manifest everytime a user interacted with our system, so whenever the manifest changes we download it and convert the SQLite3 to Postgres and store it in the same server that is storing our character's loadouts.
      The following shell script and accompanying sql file will bootstrap a fresh database to set it up ready to use for both Destiny Loadouts (storing/retrieving the loadouts) and to hold a copy of the manifest:
      * bootstrap-db.sh
      * bootstrap-db.sql
     
      Then the following shell script is used as a cron job to populate the manifest in the postgres database from the source in bungie's API.
      * bungie-manifest-refresh.sh

  4) In addition to all that, you'll need a developer account with Amazon: https://developer.amazon.com
  
  5) And you'll need the "Interaction Model" (which isn't provided here yet) plugged into your Alexa Skill so that it teaches Alexa how to interpret voice commands into the python functions in main.py.
  
  
  



