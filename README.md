[![Build Status ]]
# mpc 
This skill allows audio playback using media play client (mpc) and daemon (mpd)
It adds voice commands to play music:
* play {music_name}
* play (track|song|title|) {track} by (artist|band|) {artist}
* play (album|record) {album} by (artist|band) {artist}
* play (any|all|my|random|some|) music 
* play playlist {playlist} 
* Play genre {genre}     
Note: genre is only framed out.  The heavy lifting code is not written yet.

## About 
Stream music from your Linux server using Mycroft! 

## Examples 
* TODO: add examples once working
* "Play Song Stitch From Emby"

## Common Play Framework
This skill supports the common play framework! For Example
* "Play The Beatles"

## Credits 
rickyphewitt, mike99mac, Mycroft developers

## Category
**Music**

## Tags
#mpc #mpd #music #skill

## License
```
            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

  0. You just DO WHAT THE FUCK YOU WANT TO.
```

## Contributing
Always looking for bug fixes, features, translation, and feedback that make the Mycroft music playing experience better!

## Troubleshooting
### Setup Connection Info
* Ensure your host, port, username, and password are set at https://account.mycroft.ai/skills

### Dev Notes
Change log:
* 29 Nov 2022  Copied skill emby-skill-mike99mac to mpc-skill-mike99mac
* 

Skill is broken down into 3 main parts
* mpc_client.py
    * An lean synchronous mpc/mpd client
* mpc_croft.py
    * Logic layer between mpc client and Mycroft
* __init__.py
    * Mycroft skill hooks

### Testing
* Unit tests should be added to the test/unit directory
 


