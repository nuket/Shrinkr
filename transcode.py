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
#
# Need:
# - --dry-run (print the files that need transcoding)

import argparse
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

    file_info = {}

    if process_output.returncode == 0:
        stream_info = json.loads(process_output.stdout)
        logging.debug(stream_info)

        this_file = stream_info['streams'][0]
        logging.debug(this_file)

        file_info['file_name']   = media_file
        file_info['codec_name']  = this_file['codec_name']
        file_info['width']       = this_file['width']
        file_info['height']      = this_file['height']
        file_info['duration']    = this_file['duration']
        file_info['file_size']   = os.path.getsize(media_file)
    else:
        file_info['duration']    = 0

    return file_info


def get_output_file_name(input_file_name, output_profile, output_container):
    basename = os.path.splitext(input_file_name)[0]
    output_file_name = '{basename}-proxy-{profile}.{container}'.format(basename=basename, profile=output_profile, container=output_container)

    return output_file_name


def file_needs_transcoding(input_file_name, output_profile, output_container):
    output_file_name = get_output_file_name(input_file_name, output_profile, output_container)

    if not os.path.isfile(output_file_name) or (float(get_file_info(output_file_name)['duration']) < float(get_file_info(input_file_name)['duration'])):
        return True

    return False


def sum_up(input_file_names):
    sum = 0

    logging.info('Summing up input file durations.')

    for input_file_name in input_file_names:
        logging.info('Getting duration for {0}'.format(input_file_name))
        file_info = get_file_info(input_file_name)
        if 'duration' in file_info:
            sum += float(file_info['duration'])

    return sum


def main():
    # Input file selectors

    input_folders = list(map(os.path.expanduser, ['~/Downloads', '~/Videos']))
    input_exts    = ['*.mp4', '*.mkv']
    input_codecs  = ['hevc']

    # Output file identifiers

    output_file_suffixes = ['-proxy']

    # Output file profiles

    output_profiles = { 
        'x264-640': 'ffmpeg -i {input} -c:v libx264 -profile:v main -filter:v "scale=640:-1" -b:v 8M -c:a copy {output}',
    }

    output_profile   = 'x264-640'
    output_container = 'mp4'

    # Logging settings

    logging_level = logging.INFO

    # Parse arguments

    parser = argparse.ArgumentParser(description='Transcode a bunch of videos into smaller proxy files.')
    parser.add_argument('--sum-durations', dest='sum_durations', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(level=logging_level)

    logging.debug(input_folders)

    # Get the list of all of the usable input files

    input_globs = list(itertools.product(input_folders, input_exts))
    input_globs = list(map(list, input_globs))
    input_globs = [os.path.join(*x) for x in input_globs]

    logging.debug(input_globs)

    input_file_names = [glob.glob(x) for x in input_globs]
    input_file_names = list(itertools.chain.from_iterable(input_file_names))
    input_file_names = [x for x in input_file_names if x.rfind('-proxy') == -1]
    input_file_names.sort()

    logging.debug(input_file_names)

    # What's the total duration of all the files to be transcoded?
    if args.sum_durations:
        logging.info('Total duration of files is: {0} seconds'.format(sum_up(input_file_names)))
        return

    # Start checking the previously-unseen or modified files for the video
    # parameters.
    #
    # Duration: 00:01:04.29, start: 0.000000, bitrate: 100072 kb/s
    # Stream #0:0(eng): Video: hevc (Main) (hvc1 / 0x31637668), yuvj420p(pc, smpte170m), 3840x2160, 100024 kb/s, SAR 1:1 DAR 16:9, 30.02 fps, 30 tbr, 90k tbn, 90k tbc (default)

    for input_file_name in input_file_names:
        # input_file_info = get_file_info(input_file_name)

        # logging.info(input_file_info)

        # output_file = '{basename}-proxy-{profile}.{container}'.format(basename=os.path.splitext(input_file_name)[0], profile=output_profile, container=output_container)

        # Check whether this video has been transcoded already for the 
        # specified output profile.

        # if not os.path.isfile(output_file) or (get_file_info(output_file)['duration'] != input_file_info['duration']):
        #     logging.info('Need to transcode this file.')
        #     logging.info('ffmpeg -i {input} -c:v libx264 -profile:v baseline -filter:v "scale=640:-1" -b:v 8M -c:a copy {output}'.format(input=input_file_name, output=output_file))

            # output_file_info = get_file_info(output_file)

        # input_file_info['output_file'] = output_file
        # input_file_info['output_file_duration'] = 0

        if file_needs_transcoding(input_file_name, output_profile, output_container):
            logging.info('File ({0}) needs transcoding.'.format(input_file_name))

            output_file_name = get_output_file_name(input_file_name, output_profile, output_container)
            transcode_cmd    = 'ffmpeg -i {input} -c:v libx264 -profile:v main -filter:v scale=640:-1 -b:v 8M -c:a copy {output}'.format(input=input_file_name, output=output_file_name)
            transcode_cmd    = transcode_cmd.split(' ')
            logging.debug(transcode_cmd)
            
            process_output = subprocess.run(args=transcode_cmd, capture_output=False)
            logging.debug(process_output)
        else:
            logging.info('File ({0}) has already been transcoded to desired output profile and container format.'.format(input_file_name))


if __name__ == '__main__':
    main()
