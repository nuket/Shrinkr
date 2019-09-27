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
import json
import logging
import os
import subprocess


def get_file_info(media_file):
    probe_cmd = 'ffprobe -v quiet -print_format json -show_streams -select_streams v:0'.split(' ')
    probe_cmd.append(media_file)

    process_output = subprocess.run(args=probe_cmd, capture_output=True)
    logging.debug(process_output)

    stream_info = json.loads(process_output.stdout)
    logging.debug(stream_info)

    this_file = stream_info['streams'][0]
    logging.debug(this_file)

    file_info = {}
    file_info['file_name']   = media_file
    file_info['codec_name']  = this_file['codec_name']
    file_info['width']       = this_file['width']
    file_info['height']      = this_file['height']
    file_info['duration']    = this_file['duration']
    file_info['file_size']   = os.path.getsize(media_file)

    return file_info


def main():
    # Input file selectors

    input_folders = list(map(os.path.expanduser, ['~/Downloads', '~/Videos']))
    input_exts    = ['*.mp4', '*.mkv']
    input_codecs  = ['hevc']

    # Output file identifiers

    output_file_suffixes = ['-proxy']

    # Output file profiles

    output_profiles = { 
        'x264-640': 'ffmpeg -i {input} -c:v libx264 -profile:v baseline -filter:v "scale=640:-1" -b:v 8M -c:a copy {output}',
    }

    output_container = 'mp4'

    logging.basicConfig(level=logging.INFO)

    logging.debug(input_folders)

    # Get the list of all of the usable input files

    input_globs = list(itertools.product(input_folders, input_exts))
    input_globs = list(map(list, input_globs))
    input_globs = [os.path.join(*x) for x in input_globs]

    logging.debug(input_globs)

    input_files = [glob.glob(x) for x in input_globs]
    input_files = list(itertools.chain.from_iterable(input_files))
    input_files = [x for x in input_files if x.rfind('-proxy') == -1]

    logging.debug(input_files)

    # Start checking the previously-unseen or modified files for the video
    # parameters.
    #
    # Duration: 00:01:04.29, start: 0.000000, bitrate: 100072 kb/s
    # Stream #0:0(eng): Video: hevc (Main) (hvc1 / 0x31637668), yuvj420p(pc, smpte170m), 3840x2160, 100024 kb/s, SAR 1:1 DAR 16:9, 30.02 fps, 30 tbr, 90k tbn, 90k tbc (default)

    logging.info('ffmpeg -i {input} -c:v libx264 -profile:v baseline -filter:v "scale=640:-1" -b:v 8M -c:a copy {output}'.format(input='hello', output='goodbye'))

    for input_file in input_files:
        # probe_cmd = 'ffprobe -v quiet -print_format json -show_streams -select_streams v:0'.split(' ')
        # probe_cmd.append(input_file)

        # process_output = subprocess.run(args=probe_cmd, capture_output=True)
        # logging.debug(process_output)

        # stream_info = json.loads(process_output.stdout)
        # logging.debug(stream_info)

        # this_file = stream_info['streams'][0]
        # logging.debug(this_file)

        # file_info = {}
        # file_info['file_name']   = input_file
        # file_info['codec_name']  = this_file['codec_name']
        # file_info['width']       = this_file['width']
        # file_info['height']      = this_file['height']
        # file_info['duration']    = this_file['duration']
        # file_info['file_size']   = os.path.getsize(input_file)

        file_info = get_file_info(input_file)

        file_info['output_file'] = '{basename}-proxy-{profile}.{container}'.format(basename=os.path.splitext(input_file)[0], profile='x264-640', container=output_container)
        file_info['output_file_duration'] = 0

        # file_info['has_proxies'] = 

        logging.info(file_info)


if __name__ == '__main__':
    main()
