#!/bin/bash
ffmpeg -framerate 0.5 -pattern_type glob -i 'out/image*.jpg' -c:v libx264 movie.mp4
