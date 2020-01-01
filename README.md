# Shrinkr

This script batch transcodes a source set of video files to a target set 
of proxy video files at a lower resolution.

If the proxy video file already exists and matches the duration of the source
video file, then this script will not do the transcode again, which means you
can run this script over and over again on a folder and only the new files that 
need transcoding will be processed.

## How It Works

The files can be selected for transcoding based on the following
characteristics:

- Source Folder(s)
- Codec (HEVC, H.264, etc.)
- Resolution (2160p, 1440p, 1080p, etc.)

Using a config file, the script will seek out the source set and select
all of the files in the specified Folder(s) that match the supplied 
Codec(s) and Resolution(s).

By default, if no config file is specified, the script will run on the
current working directory (cwd) and convert all 2160p HEVC files to 
540p proxy videos.

The script will set the Date and Time values of the proxy video file 
to be identical to the source file values, so that sorting by Date Modified 
in Windows Explorer will list the two files next to one another.

## Config File

The config file is in JSON format and looks like this:

```
{
       
}
```

## Rationale

Since my computer is from the pre-Skylake generation, playback of HEVC-encoded
video is impossibly slow and editing is impossible without extra hardware support
or an additional discrete graphics card.

ffmpeg doesn't quite have a feature that lets it overwrite incomplete transcodes
and preserve completed files, it is all-or-nothing when using *.mp4-style globs.

This script gives a little more flexibility when trying to transcode files down
to editable or even viewable sizes.

## License

```
Shrinkr
Copyright (c) 2019 - 2020 Max Vilimpoc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```