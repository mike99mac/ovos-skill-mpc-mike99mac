[![Build Status ]]
# mpc 
This skill allows audio playback using music player client (mpc) and music player daemon (mpd). It supports the indexing and playback of local or network music files such as mp3 and many other formats. It also supports Internet radio stations.
It adds voice commands to play music:
* play {music_name}
* play (track|song|title|) {track} by (artist|band|) {artist}
* play (album|record) {album} by (artist|band) {artist}
* play (any|all|my|random|some|) music 
* play playlist {playlist} 
* play genre {genre}     

## About 
Stream music files or Internet radio status from your Linux server using Mycroft powered by OVOS and Neon.

## Examples 
* play track yeserday
* play album abbey road 
* play artist the beatles
* play the radio
* play genre country from the radio

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
Turn debug mode on and many messages will be written to the log files, usually skills.log;

Skill is broken down into these filess
* mpc_client.py
    * An lean synchronous mpc/mpd client
* __init__.py
    * Mycroft skill hooks

### Testing
* TODO: Unit tests should be added to the test/unit directory
 
