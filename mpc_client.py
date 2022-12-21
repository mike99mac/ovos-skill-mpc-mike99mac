#
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE FUCK YOU WANT TO.
#
from dataclasses import dataclass
from enum import Enum
import json
import logging
from .music_info import Music_info
from pathlib import Path
import random
import urllib.parse
from random import shuffle
import re
import requests
import subprocess
from typing import Union, Optional, List, Iterable

class MpcClient():
    """ Handle communication to mpd using mpc calls """
    music_dir: Path

    def __init__(self, music_dir: Path):
      self.log = logging.getLogger(__name__)
      self.music_dir = music_dir

    def update(self, wait: bool = True):
      """ Updates MPD database """
      cmd = ["mpc", "update"]
      if wait:
        cmd.append("--wait")
      self.log.info(cmd)
      subprocess.check_call(cmd)
    
    def random_play(self):
      """ Find all files and play them in random order """
      command_type = "listall"
      results = self._search(command_type)
      random.shuffle(results)
     
    def _search_music(self, command_type: str, query_type: Optional[str] = None, music_name: Optional[str] = None) -> List[List[str]]:
      """
      This handles two cases. One: a search for a particular song, artist, etc.
      Two: a 'listall' command to return all music.
      mpc syntax: https://www.musicpd.org/doc/mpc/html/#cmdoption-f
      """
      self.log.log(20, "_search_music(): command_type = "+command_type+" query_type = "+query_type+" music_name = "+music_name)
      cmd = ["mpc", command_type, "--format", "%artist%\t%album%\t%title%\t%time%\t%file%"]
      if query_type:
        cmd.extend([query_type, music_name])
      self.log.debug("_search_music(): cmd = ", cmd)
      return [
        line.split("\t")
        for line in subprocess.check_output(cmd, universal_newlines=True).splitlines()
        if line.strip()
      ]

    def _time_to_seconds(self, time_str: str) -> int:
        parts = time_str.split(":", maxsplit=2)
        assert parts
        hours, minutes, seconds = 0, 0, 0

        if len(parts) == 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        elif len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
        else:
            seconds = int(parts[0])

        return (hours * 60 * 60) + (minutes * 60) + seconds

    # Music playing vocabulary:
    # play {music_name}
    # play (track|song|title|) {track} by (artist|band|) {artist}
    # play (album|record) {album} by (artist|band) {artist}
    # play (any|all|my|random|some|) music 
    # play (playlist) {playlist}
    # play (genre) {genre}     
    #
    def parse_music(self, phrase):
      """
      Perform "brute force" parsing of a music play request
      Returns: Music_info object 
      """
      artist_name = "unknown-artist"
      found_by = "yes"                     # assume "by" is in the phrase
      intent = "unknown"                   # album, album-artist, artist, genre, music, playlist,
                                           #   track, track-artist, unknown-artist or unknown
      match_type = "unknown"               # album, artist, song or unknown
      music_name = ""                      # search term of music being sought
      track_files = []                      # files of songs to be played

      phrase = phrase.lower()
      self.log.log(20, "parse_music() phrase in lower case: " + phrase)

      # check for a partial request with no music_name
      match phrase:
        case "album" | "track" | "song" | "artist" | "genre" | "playlist":
          self.log.log(20, "parse_music() not enough information in request "+str(phrase))
          mesg_info = {"phrase": phrase}
          self.log.log(20, "parse_music() mesg_info = "+str(mesg_info))
          ret_val = Music_info("song", "not_enough_info", {"phrase": phrase}, None)
          self.log.log(20, "parse_music() ret_val.mesg_info = "+str(ret_val.mesg_info))
          return ret_val
      key = re.split(" by ", phrase)
      if len(key) == 1:                    # did not find "by"
        found_by = "no"
        music_name = str(key[0])           # check for all music, genre and playlist
        self.log.log(20, "parse_music() music_name = "+music_name)
        match music_name:
          case "any music" | "all music" | "my music" | "random music" | "some music" | "music":
            self.log.log(20, "parse_music() removed keyword "+music_name+" from music_name")
            track_files = self.get_music("music", music_name, artist_name)
            ret_val = Music_info("song", "playing_random", {}, track_files)
            return ret_val
        key = re.split("^genre ", music_name)
        if len(key) == 2:                  # found first word "genre"
          genre = str(key[1])
          self.log.log(20, "parse_music() removed keyword "+music_name+" from music_name")
          ret_val = self.get_music("genre", genre, artist_name)
          return ret_val 
        else:
          key = re.split("^playlist ", music_name)
          if len(key) == 2:                # found first word "playlist"
            playlist = str(key[1])
            self.log.log(20, "parse_music() removed keyword "+music_name+" from music_name")
            ret_val = self.get_music("playlist", playlist, artist_name)
            return ret_val
      elif len(key) == 2:                  # found one "by"
        music_name = str(key[0])
        artist_name = str(key[1])          # artist name follows "by"
        self.log.log(20, "parse_music() found the word by - music_name = "+music_name+" artist_name = "+artist_name)
      elif len(key) == 3:                  # found "by" twice - assume first one is in music
        music_name = str(key[0]) + " by " + str(key[1]) # paste the track or album back together
        self.log.log(20, "parse_music() found the word by twice: assuming first is music_name")
        artist_name = str(key[2])
      else:                                # found more than 2 "by"s - what to do?
        music_name = str(key[0])

      # look for leading keywords in music_name
      key = re.split("^album |^record ", music_name)
      if len(key) == 2:                    # found first word "album" or "record"
        match_type = "album"
        music_name = str(key[1])
        if found_by == "yes":
          intent = "album-artist"
        else:
          intent = "album"
        self.log.log(20, "parse_music() removed keyword album or record")
      else:                                # leading "album" not found
        key = re.split("^track |^song |^title ", music_name)
        if len(key) == 2:                  # leading "track", "song" or "title" found
          music_name = str(key[1])
          match_type = "song"
          if found_by == "yes":            # assume artist follows 'by'
            intent = "track-artist"
          else:                            # assume track
            intent = "track"
          self.log.log(20, "parse_music() removed keyword track, song or title")
        else:                              # leading keyword not found
          key = re.split("^artist |^band ", music_name) # remove "artist" or "band" if first word
          if len(key) == 2:                # leading "artist" or "band" found
            music_name = "all_music"       # play all the songs they have
            artist_name = str(key[1])
            match_type = "artist"
            intent = "artist"
            self.log.log(20, "parse_music() removed keyword artist or band from music_name")
          else:                            # no leading keywords found yet
            self.log.log(20, "parse_music() no keywords found: in last else clause")
            if found_by == "yes":
              intent = "unknown-artist"    # found artist but music could be track or album
      key = re.split("^artist |^band ", artist_name) # remove "artist" or "band" if first word
      if len(key) == 2:                    # leading "artist" or "band" found in artist name
        artist_name = str(key[1])
        self.log.log(20, "parse_music() removed keyword artist or band from artist_name")
      self.log.log(20, "parse_music() calling get_music with: "+intent+", "+music_name+", "+artist_name)
      ret_val = self.get_music(intent, music_name, artist_name)
      return ret_val

    def get_album(self, album_name, album_id, artist_name):
      """
      return files for one album 
      """
      self.log.log(20, "get_album() album_name = "+album_name+" artist_name = "+artist_name)
      artist_found = "none"
      results = self._search_music("search", "album", album_name)    
      num_hits = len(results)
      self.log.log(20, "get_album() num_hits = " + str(num_hits))
      if num_hits == 0: 
        self.log.log(20, "get_album() _get() did not find an album matching "+str(album_name))
        mesg_file = "music_not_found"
        mesg_info = {"album_name": album, "artist_name": artist}
        return Music_info(None, mesg_file, mesg_info, [])
      
      # at least one hit
      track_files = []
      correct_artist = True
      for artist_found, album_found, title, time_str, relative_path in results:
        if album_found.lower() != album_name: # not an exact match
          self.log.log(20, "get_album() skipping album found that does not match: "+album_found.lower())
          continue 
        next_track='"'+self.music_dir + relative_path+'"'  
        self.log.log(20, "get_album() adding track: "+next_track+" to queue")     
        track_files.append(next_track) # add track to queue
        if artist_name != "unknown-artist" and artist_name != artist_found.lower(): # wrong artist  
          correct_artist = False
      if correct_artist == False:    
        self.log.log(20, "get_album() playing album "+str(album_name)+" by "+str(artist_found)+" not by "+str(artist_name))
        mesg_file = "diff_album_artist"
        mesg_info = {"album_name": album_name, "artist_found": artist_found, "artist_name": artist_name}
      else:   
        self.log.log(20, "get_album() found album "+str(album_name)+" by artist"+artist_found)    
        mesg_file = "playing_album"
        mesg_info = {"album_name": album_found, "artist_name": artist_found}
      return Music_info("album", mesg_file, mesg_info, track_files)

    def get_artist(self, artist_name, artist_id):
      """
      return track files for artist either by ID if passed or by artist_name
      """
      track_files = []                      # return value
      self.log.log(20, "get_artist() called with artist_name "+str(artist_name))
      if artist_id == -1:                  # need to find it
        artist_encoded = urllib.parse.quote(artist_name) # encode artist name
        url = '{0}{1}&{2}{3}'.format(ITEMS_ARTIST_ID_URL, artist_encoded, API_KEY, self.auth.token)
        self.log.log(20, "get_artist() getting artist ID with mpc API: "+str(url))
        artist = self._get(url)            # search for artist
        artist_json = artist.json()        # convert to JSON
        num_artists = artist_json["TotalRecordCount"]
        self.log.log(20, "get_artist() num_artists = "+str(num_artists))
        if num_artists == 0:               # artist not found
          self.log.log(20, "get_artist() did not find music for artist "+str(artist))
          ret_val = Music_info("Artist", None, None, None)
          return ret_val
        artist_id = artist_json["Items"][0]["Id"]
        self.log.log(20, "get_artist() found artist ID "+artist_id+" with mpc API: "+str(url))

      # have artist ID, get the tracks
      url = ITEMS_SONGS_BY_ARTIST_URL + str(artist_id) + "&" + API_KEY + self.auth.token
      self.log.log(20, "get_artist() getting songs by artist with url: "+str(url))
      tracks = self._get(url)
      self.log.log(20, "get_artist() found tracks: "+str(tracks))
      tracks_json = tracks.json()
      num_recs = tracks_json["TotalRecordCount"]
      self.log.log(20, "get_artist() number of records found = "+str(num_recs))
      ret_val = Music_info("artist", "", {}, track_files)
      return ret_val
 
    def get_all_music(self):
      """
      Return random tracks files from all music
      """
      self.log.log(20, "get_all_music() play full random music")
      
      ret_val = Music_info("song", "", {}, track_files)
      return ret_val
      
    def get_genre(self, genre):
      """
      Given a genre name, return track files 
      """
      self.log.log(20, "TODO: finish code in get_genre() play genre: "+genre)
      ret_val = Music_info("song", None, None, None)
      return ret_val

    def get_playlist(self, playlist):
      """
      Search for playlist and if found, return all tracks
      """    
      self.log.log(20, "get_playlist() called with playlist: "+playlist)
     
     
      return Music_info("song", "", {}, track_files)
      
    def get_track(self, track_name, artist_name):
      """
      Get track by name, optionally by a specific artist
      If artist is not specified, it is passed in as "unknown_artist"
      """
      self.log.log(20, "get_track() called with track_name "+track_name+" artist_name "+artist_name)
      results = self._search_music("search", "title", track_name)    
      num_recs = len(results)
      if num_recs == 0:                    # no hits
        self.log.log(20, "get_track(): did not find a track matching"+track_name)
        if artist_name == "unknown_artist":
          mesg_file = "track_not_found"
          mesg_info = {"track_name": track_name}
        else:
          mesg_file = "track_artist_not_found"
          mesg_info = {"track_name": track_name, "artist_name": artist_name}   
        return Music_info(None, mesg_file, mesg_info, [])  
      
      # one or more hits
      exact_match = -1                     # no exact match yet
      index = 0
      track_files = []                     # return value(s)
      possible_files = []                  # possible return values
      possible_artists = []                # corresponding artists
      possible_albums = []                 # corresponding albums
      for artist_found, album_found, track_found, time_str, relative_path in results:
        if track_found.lower() == track_name: # track name matches
           possible_files.append('"'+self.music_dir + relative_path+'"')
           possible_artists.append(artist_found)
           possible_albums.append(album_found)
           if artist_name != "unknown_artist" and artist_found.lower() == artist_name: # exact match
             exact_match = index
             break
        index += 1
      if exact_match == -1:                # track and artist do not both match 
        if index > 0:                      # multiple hits
          num_hits = len(possible_files)
          index = random.randrange(num_hits) # choose a random track 
          self.log.log(20, "get_track() random track index = "+str(index)) 
      track_files.append(possible_files[index])
      mesg_file = "playing_track"
      mesg_info = {'track_name': track_name, 'artist_name': possible_artists[index], 'album_name': possible_albums[index]}
        
      # if artist was specified, verify it is correct
      if artist_name != "unknown-artist" and artist_name != artist_found: # wrong artist - speak correct artist before playing 
        self.log.log(20, "get_track() playing track "+str(album_found)+" by "+str(artist_found)+" not by "+str(artist_name))
        mesg_file = "diff_artist"
        mesg_info = {"track_name": track_name, "album_name": album_found, "artist_found": artist_found, "artist_name": artist_name}
      return Music_info("song", mesg_file, mesg_info, track_files) 

    def get_unknown_music(self, music_name, artist_name):
      """
      Search on a music search term - could be album, artist or track
      """
      self.log.log(20, "get_unknown_music() music_name = "+music_name+" artist_name = "+artist_name)
      track_files = []                     # list of tracks to play
      for music_type in ["artist", "album", "title"]:
        results = self._search_music("search", music_type, music_name)    
        num_recs = len(results)
        if num_recs == 0:                  # no hit
          continue                         # iterate loop
        self.log.log(20, "get_unknown_music() found "+str(num_recs)+" hits with music_type = "+music_type)  
        match music_type:
          case "artist":                   
            for artist, album, title, time_str, relative_path in results:
              if artist.lower() == music_name: # exact match
                track_files.append('"'+self.music_dir + relative_path+'"')
            num_exact = len(track_files)
            if num_exact == 0:
              continue                     # iterate loop
            else:      
              mesg_info = {"artist_name": artist}
              ret_val = Music_info("artist", "playing_artist", mesg_info, track_files)
          case "album":                    # queue multiple tracks
            for artist, album, title, time_str, relative_path in results:
              track_files.append(self.music_dir + relative_path)
            mesg_info = {"album_name": album, "artist_name": artist}
            ret_val = Music_info("album", "playing_album", mesg_info, track_files)
          case "title":                    # queue one track
            index = random.randrange(num_recs) # choose a random track 
            self.log.log(20, "get_unknown_music() random track index = "+str(index))
            track_files.append('"'+self.music_dir+results[index][4]+'"') # relative path is fifth value 
            self.log.log(20, "get_unknown_music() track_files = "+str(track_files))
            mesg_info = {"track_name": results[index][2], "album_name": results[index][1], "artist_name": results[index][0]}
            ret_val = Music_info("song", "playing_track", mesg_info, track_files)
        return ret_val   

      # if we fall through, no music was found 
      self.log.log(20, "search_music(): did not find music matching "+music_name) 
      return Music_info(None, "music_not_found", {"music_name": music_name}, None )
      
    def get_music(self, intent, music_name, artist_name):
      """
      Search for track_files with one search terms and an optional artist name
      intent can be: album, album-artist, artist, music, track, track-artist, unknown-artist or unknown
      call one of:
        get_album()         play an album
        get_artist()        play an artist
        get_all_music()     play "full random" 
        get_genre()         play a music genre 
        get_playlist()      play a saved playlist
        get_track()         play a specific track
        get_unknown_music() play something that might be a album, artist or track 
      Return: Music_info object  
      """
      self.log.log(20, "get_music() intent = "+intent+" music_name = "+music_name+" artist_name = "+artist_name) 
      match intent:
        case "album":
          ret_val = self.get_album(music_name, -1, "unknown-artist") # no album id
        case "album-artist":
          ret_val = self.get_album(music_name, -1, artist_name) # no album id
        case "artist":
          ret_val = self.get_artist(artist_name, -1) # no artist_id 
        case "genre":                   
          ret_val = self.get_genre(music_name) 
        case "music":                      # full random
          ret_val = self.get_all_music()
        case "playlist": 
          ret_val = self.get_playlist(music_name)  
        case "track":                      # call get_track with unknown track ID
          ret_val = self.get_track(music_name, "unknown-artist")
        case "track-artist":           
          ret_val = self.get_track(music_name, artist_name)
        case "unknown-artist":
          ret_val = self.get_unknown_music(music_name, artist_name)
        case "unknown":
          ret_val = self.get_unknown_music(music_name, "unknown-artist")
        case _:                            # unexpected
          self.log.log(20, "get_music() INTERNAL ERROR: intent is not supposed to be: "+str(intent))
          ret_val = Music_info(None, None, None, None) 
      return ret_val
    
    def get_id_from_uri(self, track_files):
      """
      Given a track file, return the track Id
      """
      self.log.log(20, "get_id_from_uri() track_files = "+str(track_files))
      key = re.split("/Audio/", str(track_files)) # track ID is to the right
      if len(key) == 1:                    # unexpected 
        self.log.log(20, "get_id_from_uri() UNEXPECTED: '/Audio/' not found in track_files")
        return None
      uri_suffix = key[1]
      key = re.split("/", uri_suffix)
      return key[0]

    def create_playlist(self, phrase):
      """
      Create requires a playlist name and music name as Mpc playlists cannot be empty
      Vocabulary:  (create|make) playlist {playlist} from (track|song|title) {track}
      """
      phrase = " ".join(phrase)            # convert list back to string
      phrase_encoded = urllib.parse.quote(phrase) # encode playlist name
      self.log.log(20, "create_playlist() called with phrase: "+phrase)
      key = re.split("from track |from song |from title ", phrase)
      if len(key) == 1:                    # unexpected 
        self.log.log(20, "create_playlist() 'from track' not found in phrase")
        mesg_info = {"phrase": phrase} 
        return 'missing_from', mesg_info
      playlist_name = key[0]
      music_name = key[1]
      self.log.log(20, "create_playlist() playlist_name = "+playlist_name+" music_name = "+music_name)

      # check if playlist already exists
      playlist_id = self.get_playlist_id(playlist_name) # search for playlist first
      if playlist_id != -1:                # it exists
        self.log.log(20, "create_playlist() playlist already exists: "+playlist_name)
        mesg_info = {"playlist_name": playlist_name} 
        return "playlist_exists", mesg_info

      # parse_music() returns files from which the track ID can be obtained (yes, a bit kludgy)
    
      music_info = self.parse_music(music_name) 
      if music_info.track_files == None:       # did not find track/album
        self.log.log(20, "create_playlist() did not find track "+music_name)
        mesg_file = "cannot_create_playlist"
        mesg_info = {"playlist_name": playlist_name, "music_name": music_name} 
        return mesg_file, mesg_info
      self.log.log(20, "create_playlist() music_info.track_files = "+str(music_info.track_files))
      track_id = self.get_id_from_uri(music_info.track_files)
      self.log.log(20, "create_playlist() track_id = "+track_id)
      payload = {'Name': playlist_name, 'Ids': track_id, 'MediaType': 'Playlists'}
      payload.update(self.get_headers())
      url = GET_PLAYLIST_URL+"?"+API_KEY+self.auth.token
      self.log.log(20, "create_playlist() url = "+url)
      self.log.log(20, "create_playlist() payload = "+str(payload))
      response = self._post(url, payload)
      self.log.log(20, "create_playlist() response.status_code = "+str(response.status_code))
      mesg_info = {'playlist_name': playlist_name}
      return "created_playlist", mesg_info

    def delete_playlist(self, playlist_name):
      """
      Delete a playlist
      Vocabulary: (delete|remove) playlist {playlist}
      """
      self.log.log(20, "delete_playlist() called with phrase: "+str(playlist_name))

      return False

    def get_playlist_track_ids(self, playlist_id):
      """
      Given a playlist ID, return all associated track IDs  
      """
      self.log.log(20, "get_playlist_track_ids() playlist_id = "+str(playlist_id)) 
      return None # for now
      return track_ids  
      
    def add_to_playlist(self, phrase):
      """
      Add a track or album to an existing playlist
      Vocabulary:
        add (track|song|title) {track} to playlist {playlist}
        add (album|record) {album} to playlist {playlist}
      """
      phrase = " ".join(phrase)            # convert list back to string
      self.log.log(20, "add_to_playlist() called with phrase: "+phrase)
      key = re.split(" to playlist| two playlist| 2 playlist ", phrase)
      if len(key) == 1:                    # did not find "to playlist"
        self.log.log(20, "add_to_playlist() ERROR 'to playlist' not found in phrase")
        return "to_playlist_missing", {} 
      music_name = key[0]
      playlist_name = key[1] 
      self.log.log(20, "add_to_playlist() music_name = "+music_name+" playlist_name = "+playlist_name)

      # verify playlist exists
      playlist_id = self.get_playlist_id(playlist_name) 
      if playlist_id == -1:                # not found
        self.log.log(20, "add_to_playlist() did not find playlist_name "+playlist_name)
        mesg_info = {'playlist_name': playlist_name}
        return "missing_playlist", mesg_info
      
      # verify track or album exists - parse_music() returns files but we want track IDs 
      music_info = self.parse_music(music_name) 
      if music_info.track_files == None:
        self.log.log(20, "add_to_playlist() did not find track or album "+music_name)
        mesg_info = {"playlist_name": playlist_name, "music_name": music_name} 
        return "playlist_missing_track", mesg_info
      self.log.log(20, "add_to_playlist() music_info.track_files = "+str(music_info.track_files))
      track_id = self.get_id_from_uri(music_info.track_files)
      self.log.log(20, "add_to_playlist() track_id = "+track_id)

      # verify track is not already in playlist
      track_ids = self.get_playlist_track_ids(playlist_id)
      self.log.log(20, "add_to_playlist() track_ids in playlist = "+str(track_ids))
      if track_id in track_ids:            # track is already in playlist
        self.log.log(20, "add_to_playlist() track_id = "+track_id)
        mesg_info = {'music_name': music_name, 'playlist_name': playlist_name}
        return "track_in_playlist", mesg_info

      # add track to playlist  
      payload = {'Ids': track_id, 'UserId': self.auth.user_id}
      payload.update(self.get_headers())
      url = GET_PLAYLIST_URL+playlist_id+'/Items?'+API_KEY+self.auth.token
      self.log.log(20, "add_to_playlist() url = "+url)
      self.log.log(20, "add_to_playlist() payload = "+str(payload))
      response = self._post(url, payload)
      self.log.log(20, "add_to_playlist() response.status_code = "+str(response.status_code))
      mesg_info = {'music_name': music_name, 'playlist_name': playlist_name}
      return "ok_its_done", mesg_info
      
    def delete_from_playlist(self, phrase):
      """
      Delete a track from a playlist
      Vocabulary:
        (remove|delete) (track|song|title) {track} from playlist {playlist}
        (remove|delete) (album|record) {album} from playlist {playlist}
      """
      self.log.log(20, "delete_from_playlist() called with phrase: "+str(phrase))
      phrase = " ".join(phrase)            # convert list back to string
      key = re.split(" from playlist ", phrase)
      if len(key) == 1:                    # did not find "from playlist"
        self.log.log(20, "delete_from_playlist() ERROR 'from playlist' not found in phrase")
        return "to_playlist_missing", {} 
      music_name = key[0]
      playlist_name = key[1] 
      self.log.log(20, "delete_from_playlist() music_name = "+music_name+" playlist_name = "+playlist_name)

      # verify playlist exists
      playlist_id = self.get_playlist_id(playlist_name) 
      if playlist_id == -1:                # not found
        self.log.log(20, "delete_from_playlist() did not find playlist_name "+playlist_name)
        mesg_info = {'playlist_name': playlist_name}
        return "missing_playlist", mesg_info
      
      # verify track or album exists - parse_music() returns files but we want track IDs 
      music_info = self.parse_music(music_name) 
      if music_info.track_files == None:
        self.log.log(20, "delete_from_playlist() did not find track or album "+music_name)
        mesg_info = {"playlist_name": playlist_name, "music_name": music_name} 
        return "playlist_missing_track", mesg_info
      self.log.log(20, "delete_from_playlist() music_info.track_files = "+str(music_info.track_files))
      track_id = self.get_id_from_uri(music_info.track_files)
      self.log.log(20, "delete_from_playlist() track_id = "+track_id)

      # remove track from playlist  
    # payload = {'Id': track_id, 'UserId': self.auth.user_id}
      payload = {'Id': track_id, 'EntryId': "1_810ne0fn"}
      payload.update(self.get_headers())
      url = ITEMS_URL+"/"+playlist_id+"?"+API_KEY+self.auth.token
      self.log.log(20, "delete_from_playlist() url = "+url)
      self.log.log(20, "delete_from_playlist() payload = "+str(payload))
      response = self._delete(url, payload)
      self.log.log(20, "delete_from_playlist() response.status_code = "+str(response.status_code))
      self.log.log(20, "delete_from_playlist() response.url = "+str(response.url))
      return "ok_its_done", {}

class MpcMediaItem(object):
    """
    Stripped down representation of a media item in Mpc
    """

    def __init__(self, id, name, type):
        self.id = id
        self.name = name
        self.type = type

    @classmethod
    def from_item(cls, item):
        media_item_type = MediaItemType.from_string(item["Type"])
        return MpcMediaItem(item["Id"], item["Name"], media_item_type)

    @staticmethod
    def from_list(items):
        media_items = []
        for item in items:
            media_items.append(MpcMediaItem.from_item(item))

        return media_items

class MediaItemType(Enum):
    ARTIST = "MusicArtist"
    ALBUM = "MusicAlbum"
    SONG = "Audio"
    OTHER = "Other"

    @staticmethod
    def from_string(enum_string):
        for item_type in MediaItemType:
            if item_type.value == enum_string:
                return item_type
        return MediaItemType.OTHER
