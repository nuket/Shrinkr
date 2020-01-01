#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

# Shrinkr Batch Transcode
# https://github.com/nuket/shrinkr
# 
# This script will batch transcode a source set of video files to a target set 
# of proxy video files at a lower resolution.
# 
# If the proxy video file already exists and matches the duration of the source
# video file, then this script will not do the transcode again, which means you
# can run this script over and over again on a folder and only the new files that 
# need transcoding will be processed.

# Shrinkr Batch Transcode
# Copyright (c) 2019 - 2020 Max Vilimpoc
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# This script requires:
# - Python 3.7 (for the subprocess capture_output param)

# Rationale
#
# Since my computer is from the pre-Skylake generation, playback of HEVC-encoded
# video is impossibly slow and editing is impossible without extra hardware support
# or an additional discrete graphics card (which I'll buy eventually, just not 
# this instant).
#
# ffmpeg doesn't quite have a feature that lets it overwrite incomplete transcodes
# and preserve completed files, it is all-or-nothing when using *.mp4-style globs.
#
# This script gives a little more flexibility when trying to transcode files down
# to editable or even viewable sizes.

# This script will:
# - Load the configuration file
# - Scan the input folders for files matching the glob (*.mp4, etc.)
# - Load the transcoding cache file (JSON list of filenames and file date + size)
# - Check for files matching the video codec
# - Transcode and rescale the files to a specific output profile

import argparse
import glob
import itertools
import json
import logging
import os
import shutil
import subprocess
import sys
import textwrap
import time

SHRINKR_CACHE_FILENAME           = 'ShrinkrCache.json'
SHRINKR_OUTPUT_PROFILES_FILENAME = 'ShrinkrOutputProfiles.json'

# Output files will have this string in them to identify them to Shrinkr.
# If an input file has this string in its name, it will be skipped.
#
# This means that Shrinkr will do its best to avoid reprocessing files
# that it has already processed.
#
# It also implies that transcoding a transcoded file should not happen, 
# meaning that Shrinkr always tries to use the highest-res source material
# possible (i.e. the original high-res video file).

SHRINKR_OUTPUT_FILE_SUFFIX = 'shrinkr'


def convert_utvideo_duration_to_float(duration):
    # Example: '00:00:15.066000000' needs to be converted to float
    hrs, mins, seconds = str(duration).split(':', 2)

    return float(hrs) * 3600.0 + float(mins) * 60.0 + float(seconds)


def get_cached_file_info(filename, cache):
    try:
        if (os.path.getmtime(filename) == cache[filename]['datetime']):
            return cache[filename]['ffprobe_data']
    except:
        pass

    return {}


def get_file_info(filename, cache):
    file_info = {}
    file_info['file_name']  = filename
    file_info['file_size']  = os.path.getsize(filename)
    file_info['codec_name'] = 'Unknown'
    file_info['width']      = 'Unknown'
    file_info['height']     = 'Unknown'
    file_info['duration']   = 0

    print('Getting file info for "{0}"'.format(filename))

    stream_info = get_cached_file_info(filename, cache)

    if not stream_info:
        probe_cmd = 'ffprobe -v quiet -print_format json -show_streams -select_streams v:0'.split(' ')
        probe_cmd.append(filename)

        process_output = subprocess.run(args=probe_cmd, capture_output=True)
        logging.debug(process_output)

        if process_output.returncode == 0:
            stream_info = json.loads(process_output.stdout)
            logging.debug(stream_info)

            # Save the ffprobe output to the cache file
            cache[filename] = {}
            cache[filename]['datetime']     = os.path.getmtime(filename)
            cache[filename]['ffprobe_data'] = stream_info

            with open(SHRINKR_CACHE_FILENAME, mode='w') as cache_fp:
                json.dump(cache, cache_fp)

    if 'streams' in stream_info.keys():
        this_file = stream_info['streams'][0]
        logging.debug(this_file)

        file_info['codec_name']   = this_file['codec_name']
        file_info['width']        = this_file['width']
        file_info['height']       = this_file['height']

        # Duration depends on what type of file it is.
        #
        # utvideo files have duration stored in ["tags"]["DURATION"] key
        # mp4 files have it in ['duration'] key

        if file_info['codec_name'] == 'utvideo':
            file_info['duration'] = convert_utvideo_duration_to_float(this_file['tags']['DURATION'])
        else:
            file_info['duration'] = this_file['duration']

    return file_info


def get_file_duration(filename, cache):
    try:
        info = get_file_info(filename, cache)
        return float(info['duration'])
    except:
        pass

    return 0.0


def get_output_file_name(input_file_name, output_profile, output_container):
    basename = os.path.splitext(input_file_name)[0]
    output_file_name = '{basename}-{tag}-{profile}.{container}'.format(basename=basename, tag=SHRINKR_OUTPUT_FILE_SUFFIX, profile=output_profile, container=output_container)

    return output_file_name


def sum_up(input_file_names):
    sum = 0

    logging.info('Summing up input file durations.')

    for input_file_name in input_file_names:
        logging.info('Getting duration for {0}'.format(input_file_name))
        file_info = get_file_info(input_file_name)
        if 'duration' in file_info:
            sum += float(file_info['duration'])

    return sum


def file_matches_selectors(input_file_name, cache, select_codecs, select_heights):
    file_info = get_file_info(input_file_name, cache)

    if file_info['codec_name'] in select_codecs and file_info['height'] in select_heights:
        return True

    return False


def generate_transcode_commands(input_file_names, cache, target_output_profiles, output_profile_defs):
    transcode_commands = []

    for input_file_name in input_file_names:
        for profile in target_output_profiles:
            if profile in output_profile_defs.keys():
                output_file_name = get_output_file_name(input_file_name, profile, output_profile_defs[profile]['container'])
                transcode_command = str(output_profile_defs[profile]['command']).format(input=input_file_name, output=output_file_name)

                input_duration  = get_file_duration(input_file_name, cache)
                output_duration = get_file_duration(output_file_name, cache)

                if not os.path.isfile(output_file_name) or (output_duration < input_duration):
                    transcode_commands.append({"command": transcode_command, "modified_time": os.path.getmtime(input_file_name), "output_file_name": output_file_name})
                else:
                    print('File "{input}" has already been transcoded to {profile}'.format(input=input_file_name, profile=profile))
            else:
                logging.warning('Profile "{profile}" not a valid profile in {profile_defs_file}.', profile=profile, profile_defs_file=SHRINKR_OUTPUT_PROFILES_FILENAME)
                
    return transcode_commands


def main():
    # Load the cached video information from previous ffprobe runs.
    #
    # If the file datetime didn't change, use the cached information
    # otherwise, run ffprobe again and cache that.

    file_info_cache = {}

    try:
        with open(SHRINKR_CACHE_FILENAME) as cache_fp:
            file_info_cache = json.load(cache_fp)
    except FileNotFoundError:
        pass

    # Output file profiles
    #
    # Very loose about this, almost any freeform ffmpeg command line can be put here.
    #
    # There are a number of keys that Shrinkr supplies for string substitution:
    # 
    # - {input}
    # - {output} 

    output_profile_defs = json.load(open("ShrinkrOutputProfiles.json"))

    # Parse arguments

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
            Transcode a bunch of videos into smaller proxy video files 
            for easier viewing and editing, without redoing files unnecessarily.
            
            Safety first: 
            Pass the --go option to actually run the generated transcoder commands!
            '''))
    parser.add_argument('--go', action='store_true', help='actually run the transcoder commands (default: %(default)s)')
    parser.add_argument('--jobfile', default='ShrinkrJob.json', help='specify other jobfile (default: %(default)s)')
    parser.add_argument('-v', default=0, type=int, help='set the debug output level (0 = INFO, 1 = DEBUG) (default: %(default)s)')
    # parser.add_argument('--sum-durations', action='store_true', help='Sum up the durations of all the input files (default: %(default)s)')
    # parser.add_argument('--fix-timestamps', action='store_true', help='go through and set the timestamps of the transcoded files to the timestamps of the original files (default: %(default)s)')

    if len(sys.argv[1:]) == 0:
        parser.print_help()

    args = parser.parse_args()

    if args.v == 1:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Check for ffmpeg in the PATH

    print()
    print('Shrinkr -------------------------------------------------------------')
    print('Check for presence of ffmpeg on PATH')
    print('---------------------------------------------------------------------')
    print()

    if not shutil.which('ffmpeg'):
        print("Couldn't find ffmpeg, so we cannot proceed")
        return

    # Load up the jobs file, which defines folders to search for input files

    job = json.load(open(args.jobfile))

    print()
    print('Shrinkr -------------------------------------------------------------')
    print("Find all input files specified via the '{0}' jobfile".format(args.jobfile))
    print('with folders    {0}'.format(job['input_folders']))
    print('with extensions {0}'.format(job['input_exts']))
    # print('that match Codec and Resolution selectors')
    print('---------------------------------------------------------------------')
    print()

    # Input file selectors

    input_folders = list(map(os.path.expanduser, job['input_folders']))
    input_folders = list(map(os.path.normpath, input_folders))

    # Get the list of all of the usable input files

    input_globs = list(itertools.product(input_folders, job['input_exts']))
    input_globs = list(map(list, input_globs))
    input_globs = [os.path.join(*x) for x in input_globs]

    input_file_names = [glob.glob(x) for x in input_globs]
    input_file_names = list(itertools.chain.from_iterable(input_file_names))
    input_file_names = [x for x in input_file_names if x.rfind(SHRINKR_OUTPUT_FILE_SUFFIX) == -1] # Don't process files containing SHRINKR_OUTPUT_FILE_SUFFIX
    input_file_names.sort()

    # What's the total duration of all the files to be transcoded?
    # if args.sum_durations:
    #     logging.info('Total duration of files is: {0} seconds'.format(sum_up(input_file_names)))
    #     return

    # Start checking the list of input files and only keep the ones that 
    # match the input selectors
    #
    # Duration: 00:01:04.29, start: 0.000000, bitrate: 100072 kb/s
    # Stream #0:0(eng): Video: hevc (Main) (hvc1 / 0x31637668), yuvj420p(pc, smpte170m), 3840x2160, 100024 kb/s, SAR 1:1 DAR 16:9, 30.02 fps, 30 tbr, 90k tbn, 90k tbc (default)

    # Filter out the input files that don't match the Codec or Height we want to transcode

    start = time.perf_counter()
    filtered_input_file_names = [x for x in input_file_names if file_matches_selectors(x, file_info_cache, job['select_codecs'], job['select_heights'])]
    end = time.perf_counter()

    logging.debug('Load and filter input files in {0} seconds'.format(end - start))

    # Create a list of input -> output transcoder commands based on desired output profiles and containers
    #
    # number of output files = (number of input files * number of desired output profiles) - number of already transcoded files

    print()
    print('Shrinkr -------------------------------------------------------------')
    print('Generate transcode commands, check which output files already exist')
    print()
    print("Obviously we won't need to transcode those files again if they match")
    print('the input file duration')
    print('---------------------------------------------------------------------')
    print()

    start = time.perf_counter()
    transcode_commands = generate_transcode_commands(filtered_input_file_names, file_info_cache, job['output_profiles'], output_profile_defs)
    end = time.perf_counter()

    logging.debug('Generated transcode commands in {0} seconds'.format(end - start))

    print()
    print('Shrinkr -------------------------------------------------------------')
    print('{0} -- these are the transcoding commands that {1} be executed:'.format(('Dry Run', 'Execute')[args.go], ('would', 'will')[args.go]))
    print('---------------------------------------------------------------------')
    print()

    if 0 == len(transcode_commands):
        print("Looks like you've already transcoded everything, nothing left to do!")
        return

    [print(c["command"]) for c in transcode_commands]

    if not args.go:
        return

    print()
    print('Shrinkr -------------------------------------------------------------')
    print('Running Transcodes')
    print('---------------------------------------------------------------------')
    print()

    for c in transcode_commands:
        print("Running: {0}".format(c["command"]))
        command = c["command"].split(' ')
        process_output = subprocess.run(args=command, capture_output=True)

        logging.debug(process_output)

        if process_output.returncode == 0:
            print("Done")
        else:
            # TODO: 
            # Make a note about this in the output file extension, rendering it
            # unplayable when doubleclicked.
            # 
            # When doing this, also need to add code to check for -error output
            # files when checking whether this file has already been transcoded.
            print("Error")
            # error_file_name = c["output_file_name"] + "-error" # i.e. .mp4-error or .mkv-error
            # os.rename(c["output_file_name"], error_file_name)
            # c["output_file_name"] = error_file_name

        # process = subprocess.Popen(args=command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True),
        # (stdout_data, stderr_data) = process.communicate()

        # Set the Date Modified value of the transcoded file to that of the input file
        print("Set transcoded file Date Modified value to {0}".format(time.ctime(c["modified_time"])))
        print()
        os.utime(c["output_file_name"], (c["modified_time"], c["modified_time"]))


if __name__ == '__main__':
    main()
