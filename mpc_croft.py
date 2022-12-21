#
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE FUCK YOU WANT TO. 
#
import logging
import subprocess
from enum import Enum
from random import shuffle
from collections import defaultdict
import json
import re
from .music_info import Music_info

try:
    # this import works when installing/running the skill - note the relative '.'
    from .mpc_client import MpcClient, MediaItemType, MpcMediaItem
except (ImportError, SystemError):
    # when running unit tests the '.' from above fails so we exclude it
    from mpc_client import MpcClient, MediaItemType, MpcMediaItem

class MpcCroft(object):
    music_dir: str

    def __init__(self, music_dir):
        self.music_dir = music_dir
        self.log = logging.getLogger(__name__)
        self.client = MpcClient(self.music_dir)

    def parse_common_phrase(self, phrase: str):
        """
        Attempts to match mpc items with phrase
        :param phrase:
        :return:
        """
        media_types = {'artist': MediaItemType.ARTIST,
                       'album': MediaItemType.ALBUM,
                       'song': MediaItemType.SONG}
        ret_val = self.client.parse_music(phrase)
        self.log.log(20, "parse_common_phrase() - returning Music_info object of type "+str(type(ret_val))) 
        return ret_val

    # Vocabulary for manipulating playlists:
    #   (create|make) playlist {playlist} from track {track}
    #   (delete|remove) playlist {playlist}
    #   add (track|song|title) {track} to playlist {playlist}
    #   add (album|record) {album} to playlist {playlist}
    #   (remove|delete) (track|song|title) {track} from playlist {playlist}
    #   (remove|delete) (album|record) {album} from playlist {playlist}
    #
    # return value is file name of .dialog file (str) to speak and any info to be added (dict)
    def manipulate_playlists(self, utterance):
      self.log.log(20, "manipulate_playlists() called with: "+utterance) 
      words = utterance.split()            # split request into words
      match words[0]:                      
        case "create" | "make":         
          mesg_file, mesg_info = self.client.create_playlist(words[2:]) 
        case "remove" | "delete":      
          if words[1] == "playlist":
            mesg_file, mesg_info = self.client.delete_playlist(words[2:]) 
          else:                       
            mesg_file, mesg_info = self.client.delete_from_playlist(words[1:]) 
        case "add":                  
          mesg_file, mesg_info = self.client.add_to_playlist(words[1:]) 
      self.log.log(20, "manipulate_playlists() returned: "+mesg_file+" and "+str(mesg_info))
      return mesg_file, mesg_info
