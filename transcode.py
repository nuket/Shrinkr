#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

# This script requires:
# - Python 3.7 (for the capture_output param)

# Since my computer is from the pre-Skylake generation, playback of HEVC coded
# video is impossibly slow and editing is impossible.
#
# This script will:
# - Load the transcoding cache file (JSON list of filenames and file date + size)
# - Scan the input folders for files matching the glob (*.mp4, etc.)
# - Check for files matching the video codec
# - Scan the input folders for files in process
# - Scale the files down
# - Reencode them to a specific output_profile


import glob
import itertools
import logging
import os
import subprocess

cache_data    = {}

input_folders = list(map(os.path.expanduser, ['~/Downloads', '~/Videos']))
input_exts    = ['*.mp4', '*.mkv']
input_codecs  = ['hevc']

output_file_suffixes = ['-proxy']

output_profile = { 'x264-640': '' }


logging.basicConfig(level=logging.INFO)

logging.info(input_folders)

input_globs = list(itertools.product(input_folders, input_exts))
input_globs = list(map(list, input_globs))
input_globs = [os.path.join(*x) for x in input_globs]

logging.info(input_globs)

input_files = [glob.glob(x) for x in input_globs]
input_files = list(itertools.chain.from_iterable(input_files))
input_files = [x for x in input_files if x.rfind('-proxy') == -1]

logging.info(input_files)

# Start checking the previously-unseen or modified files for the video
# parameters.
#
# Duration: 00:01:04.29, start: 0.000000, bitrate: 100072 kb/s
# Stream #0:0(eng): Video: hevc (Main) (hvc1 / 0x31637668), yuvj420p(pc, smpte170m), 3840x2160, 100024 kb/s, SAR 1:1 DAR 16:9, 30.02 fps, 30 tbr, 90k tbn, 90k tbc (default)

probe_cmd = 'ffprobe -v quiet -print_format json -show_streams -select_streams v:0'.split(' ')
probe_cmd.append(input_files[0])

output = subprocess.run(args=probe_cmd, capture_output=True)
print(output)
