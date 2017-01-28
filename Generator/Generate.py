import os
import subprocess
import sys
import time

sys.path.append("..")

from Config import *

class Song:
    def __init__(self):
        self.FileName = ""
        self.SongName = ""
        self.Album = ""
        self.AlbumArt = ""
        self.Artist = ""
        self.DownloadLink = ""
        self.License = ""
        self.Minutes = -1
        self.Seconds = -1
        self.AttributionInfo = ""

# Set Environmental Variables for FFMPEG.
os.environ["FC_CONFIG_DIR"] = FC_CONFIG_DIR
os.environ["FONTCONFIG_FILE"] = FONTCONFIG_FILE
os.environ["FONTCONFIG_PATH"] = FONTCONFIG_PATH

# Check for output directory
if (os.path.exists(OUTPUT_DIR) == False):
    os.mkdir(OUTPUT_DIR)
elif(os.path.isdir(OUTPUT_DIR) == False):
    raise NotADirectoryError(OUTPUT_DIR + " already exists, but is not a directory.  Abort")

# Parse CSV
with open(INPUT_FILE, 'r') as inFile:
    data = inFile.read()

rootDir = os.path.dirname(INPUT_FILE)

SongList = []

i = 0
for line in data.splitlines():
    # Skip the first two lines
    if (i < 2):
        i += 1
        continue

    splitString = line.split('\t')
    song = Song()
    song.FileName = os.path.join(rootDir, splitString[0])
    song.SongName = splitString[1]
    song.Album = splitString[2]
    song.Artist = splitString[3]
    song.DownloadLink = splitString[4]
    song.License = splitString[5]
    song.Minutes = splitString[6]
    song.Seconds = splitString[7]
    song.AttributionInfo=splitString[8]

    if (song.AttributionInfo == ""):
        song.AttributionInfo = song.SongName + " by " + song.Artist + ". Licensed under " + song.License + ". " + song.DownloadLink

    albumArtPath = os.path.join(os.path.basename(song.FileName), "AlbumArt.jpg")
    if (os.path.exists(albumArtPath) and os.path.isfile(albumArtPath)):
        song.AlbumArt = albumArtPath
    else:
        song.AlbumArt = DEFAULT_ALBUM_ART

    SongList += [song]

for song in SongList:

    # Write text.txt (crappy workaround that beats command line shenigans)
    with open("info.txt", 'w') as outFile:
        outFile.write(song.SongName + " by " + song.Artist + "\n")
        outFile.write("Album: " + song.Album + "\n")
        outFile.write("License: " + song.License + "\n")
        outFile.write("\n")
        outFile.write("\n")

    # Need to escape C:\ in Windows (ffmpeg uses : as arg separators).
    escaptedFontFile = FONT_FILE.replace(":", "\\\\:")

    outputFile = os.path.join(OUTPUT_DIR, song.SongName + ".flv")

    ffmpegArgs = [
        FFMPEG_PATH,
        "-i", song.FileName,
        "-loop", "1", "-i", song.AlbumArt,
        "-loop", "1", "-i", "xlogo.png",
        "-filter_complex",
        'color=c=black:size=1280x720[base];' + \
        '[0:a]showwaves=s=1280x200:mode=line[waves];' + \
        '[0:a]avectorscope=m=lissajous:s=600x600:draw=line[vs];' + \
        '[1:v]setpts=PTS-STARTPTS, scale=300x300[albumArt];' + \
        '[2:v]setpts=PTS-STARTPTS, scale=482x191[xlogo];' + \
        '[base][waves]overlay=shortest=1:x=10:y=560[tmp0];' + \
        '[tmp0][vs]overlay=shortest=1:x=500:y=10[tmp1];' + \
        '[tmp1][albumArt]overlay=shortest=1:x=10:y=300[tmp2];' + \
        '[tmp2]drawtext=fontfile=' + escaptedFontFile + ":fontsize=20:fontcolor=yellow:x=10:y=215:text='https\\://meditationenthusiasts.org/'[tmp3];" +\
        '[tmp3]drawtext=fontfile=' + escaptedFontFile + ":fontsize=24:fontcolor=white:x=10:y=270:text='Now Playing\\:'[tmp4];" + \
        '[tmp4]drawtext=fontfile=' + escaptedFontFile + ":box=1:boxcolor=black:fontsize=24:fontcolor=white:x=10:y=610:boxborderw=10:textfile='info.txt'[tmp5];" + \
        '[tmp5]drawtext=fontfile=' + escaptedFontFile + ":fix_bounds=1:box=1:boxcolor=black:fontsize=16:fontcolor=white:x=w-mod(t*(w+tw)/30.0\,(w+tw)):y=15:boxborderw=10:text='" + song.AttributionInfo.replace(":", "\\:") + "'[tmp6];" + \
        '[tmp6][xlogo]overlay=shortest=1:x=-2:y=10[out]',
        "-map", '[out]',
        "-map", "0:a",
        "-vcodec", "libx264",
        "-preset", "medium",
        "-maxrate", "3000k",
        "-bufsize", "6000k",
        "-g", "50",
        "-acodec", "libmp3lame",
        "-b:a", "128k",
        "-ac", "2",
        "-ar", "44100",
        "-shortest", outputFile
    ]

    print("Converting " + song.SongName )
    proc = subprocess.Popen(ffmpegArgs, stdin = subprocess.PIPE)

    ###
    # FFMPEG sometimes won't exit.
    # If the file size doesn't change, send the exit command.
    ###
    sameCount = 0
    lastSize = 0
    while sameCount < 5:
        if (os.path.exists(outputFile) == False):
            continue

        currentSize = os.path.getsize(outputFile)
        if (currentSize == lastSize):
            sameCount += 1
        else:
            sameCount = 0

        lastSize = currentSize

        time.sleep(0.5)

    proc.stdin.write(b"q")
    proc.stdin.flush()
    success = proc.wait()

    if (success != 0):
        print ("Could not convert " + song.SongName)
