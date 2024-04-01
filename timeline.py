#!/usr/bin/env python3

'''
This program reads a set of photos 
of a construction project underway 
over the period of many months.
'''

import os
import math
import datetime as dt

# read the EXIF and metadata from the photos
import exifread as ex

# PIL used to draw on the images
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 
from PIL import ImageOps

# ffmpeg used to make the movie
import ffmpeg

# we used the font_manager from matplotlib
# to find the desired font file
from matplotlib import font_manager

# hard-coded list of images, could be automated by globbing.
default_images_pathname = 'images'
list_of_images = [
  'IMG_6590.jpeg', 'IMG_6777.jpeg', 'IMG_6789.jpeg',
  'IMG_6854.jpeg', 'IMG_7086.jpeg', 'IMG_7098.jpeg', 'IMG_7128.jpeg',
  'IMG_7130.jpeg', 'IMG_7131.jpeg', 'IMG_7194.jpeg', 'IMG_7250.jpeg',
  'IMG_7466.jpeg', 'IMG_7483.jpeg', 'IMG_7506.jpeg', 'IMG_7508.jpeg',
  'IMG_7511.jpeg', 'IMG_7526.jpeg', 'IMG_7536.jpeg', 'IMG_7547.jpeg',
  'IMG_7561.jpeg', 'IMG_7571.jpeg', 'IMG_7618.jpeg', 'IMG_7643.jpeg',
  'IMG_7651.jpeg', 'IMG_7652.jpeg', 'IMG_7693.jpeg', 'IMG_7702.jpeg',
  'IMG_7705.jpeg', 'IMG_7708.jpeg', 'IMG_7725.jpeg', 'IMG_7737.jpeg',
  'IMG_7746.jpeg', 'IMG_7762.jpeg', 'IMG_7788.jpeg', 'IMG_7811.jpeg',
  'IMG_7826.jpeg', 'IMG_7846.jpeg', 'IMG_7922.jpeg', 'IMG_7942.jpeg', 
  'IMG_7955.jpeg', 'IMG_7956.jpeg', 'IMG_7995.jpeg', 'IMG_8046.jpeg',
]

# movie file name
filename_movie = 'movie.mp4'
# image default filename (for testing)
default_outfile = 'sample-out.jpg'
# modified images filenames (see Frames.evaluate():
#   outfile = f'tmp/image{i:03d}.jpg'

class Frame:
  '''Photo object, associated helper functions and parameters.'''
  def __init__( self, filename, pathname=default_images_pathname ):
    '''Opens and evaluates data in a photo, has overlay functions.'''
    self.filename = filename
    self.pathname = pathname
    self.fullpath = '/'.join( [self.pathname, self.filename] )
    self.outfile = default_outfile
    with open(self.fullpath, 'rb') as fp:
      # evaluate the EXIF data, fetching info of interest
      self.tags = ex.process_file(fp)
    self.get_datetime()
    self.get_resolution()
    self.get_latlon()
    # set up the font details for text overlay
    self.font_obj = font_manager.FontProperties(family='D2coding', weight='bold')
    self.font_file = font_manager.findfont(self.font_obj)
    self.font_size_percent = 1.5
    self.font_size = self.font_size_percent * self.diag / 100
    self.font = ImageFont.truetype( self.font_file, self.font_size )
  # Example of image size data
  #   EXIF ExifImageLength (Long): 3024
  #   EXIF ExifImageWidth (Long): 4032
  def get_resolution( self ):
    '''Fetches image resolution.'''
    self.height = self.tags['EXIF ExifImageLength'].values[0]
    self.width = self.tags['EXIF ExifImageWidth'].values[0]
    self.size = f'{self.width}x{self.height}'
    self.diag = math.sqrt( self.height*self.height + self.width*self.width )
    # reduce the size to QuadVGA 1280x960 (4:3, matches photos)
    self.outsize = (1280, 960)
    self.outsize_str = f'{self.outsize[0]}x{self.outsize[1]}'
  # Example of GPS data and format
  #   GPS GPSLatitude (Ratio): [36, 23, 2153/100]
  #   GPS GPSLatitudeRef (ASCII): N
  #   GPS GPSLongitude (Ratio): [127, 21, 1877/50]
  #   GPS GPSLongitudeRef (ASCII): E
  #   GPS GPSAltitude (Ratio): 42657/668
  def to_dms(self, val, ref):
    d = val.values[0].decimal()
    m = val.values[1].decimal()
    s = val.values[2].decimal()
    return f'{ref}{d:03.0f}.{m:02.0f}.{s:03.0f}'
  def get_latlon( self ):
    '''Gets and formats lat/lon of camera from EXIF.'''
    val = self.tags['GPS GPSLatitude']
    ref = self.tags['GPS GPSLatitudeRef']
    self.lat = self.to_dms(val, ref)
    val = self.tags['GPS GPSLongitude']
    ref = self.tags['GPS GPSLongitudeRef']
    self.lon = self.to_dms(val, ref)
    alt = self.tags['GPS GPSAltitude'].values[0].decimal()
    self.alt = f'{alt:.1f}'

  # Example of date-time format
  #   Image DateTime (ASCII): 2021:10:13 15:11:16
  def get_datetime( self ):
    '''Gets the date and time from EXIF.'''
    datetime_exif = self.tags['Image DateTime'].values
    self.datetime_obj = dt.datetime.strptime(datetime_exif, '%Y:%m:%d %H:%M:%S')
    self.datetime = dt.datetime.strftime( self.datetime_obj, '%d-%b-%Y %H:%M:%S')
    self.datetime_label = dt.datetime.strftime( self.datetime_obj, '%d-%b-%Y')
    self.datetime_short = dt.datetime.strftime( self.datetime_obj, '%d-%b-%Y %H:%M')
    self.timediff = dt.timedelta() # makes zero timediff
    self.tprogress = dt.timedelta()
    self.tprogress_frac = 0 # 0 to 1.0, fraction of total progress
    self.tprogress_hours = 0

  def print( self ):
    '''Prints out the key info for the frame.'''
    # print( self.fullpath, self.datetime, self.lat, self.lon, self.alt, self.size )
    print( self.filename, self.size, self.datetime_short, self.outfile, self.outsize_str)

  def print_times( self ):
    '''Prints out date and time of the frame.'''
    print( f'{self.filename}   {self.datetime} {self.timediff.__str__():>18}' 
          f'{self.tprogress_hours:>8} hrs ( {self.tprogress_frac*100:>5.1f}% )' )


  def load(self):
    '''Load the frame, normailize any rotation.'''
    image = Image.open(self.fullpath)
    self.image = ImageOps.exif_transpose(image)

  def overlay_text( self, 
    text = "Sample Text", 
    position = (10, 10) ):
    '''Adds overlay text to the image.'''
    draw = ImageDraw.Draw(self.image)
    left, top, right, bottom = draw.textbbox(position, text, font=self.font)
    draw.rectangle((left-5, top-5, right+5, bottom+5), fill="red")
    draw.text(position, text, font=self.font, fill="black")

  def timeline( self ):
    color_background = 'black'
    color_progress = 'red'
    color_timeline = 'gray'
    color_label = 'white'
    draw = ImageDraw.Draw(self.image) 
    rad = 15 # progress dot radius
    line_wid = 10
    # position and size of timeline
    xlen = 0.95 * self.width
    xoff = ( self.width - xlen ) / 2.0
    yoff = 0.98 * self.height
    # progress along timeline
    xprog = xoff + xlen * self.tprogress_frac
    # label 
    label = self.datetime_label
    xlab = xprog
    ylab = yoff - 1.25*rad
    left, top, right, bottom = self.font.getbbox(label)
    span = right - left # length of bounding box pixels
    height = bottom - top
    # background box 
    box_xlen = self.width
    box_ylen = self.height-yoff + 2.25*rad + 1.5*height
    box_xoff = 0
    box_yoff = self.height
    # Now draw everything...
    # ... timeline background box
    box = ( box_xoff, box_yoff-box_ylen,  box_xoff+box_xlen, box_yoff )
    draw.rectangle( box, fill=color_background )
    # ... the timeline itself
    timeline = (xoff, yoff,     xoff+xlen, yoff)
    draw.line( timeline, fill=color_timeline, width=line_wid )
    # ... the progress dot and line
    progress = ( xprog-rad, yoff-rad,   xprog+rad, yoff+rad )
    draw.ellipse( progress, fill=color_progress, width=1 )
    progline = (xoff, yoff,    xprog, yoff) 
    draw.line( progline, fill=color_progress, width=2*rad )
    # ... label the progress dot
    if xprog - 0.5*span < xoff:
      # the label would be cut off by the left-most edge of timeline
      position = (xoff, ylab)
      draw.text(position, label, anchor = 'ld', font=self.font, 
                fill=color_label)
    elif (xprog + 0.5*span) > (xoff+xlen):
      # the label would be cut off by the right-most edge of timeline
      position = (xoff+xlen, ylab)
      draw.text(position, label, anchor = 'rd', font=self.font,
                fill=color_label)
    else:
      # center justify the label over the progress point
      position = (xprog, ylab)
      draw.text(position, label, anchor = 'md', font=self.font,
                fill=color_label)

  def save( self, outfile=None ):
    '''Saves the image with the overlaid text.'''
    if outfile is None: outfile = self.outfile
    self.image.thumbnail(self.outsize, Image.LANCZOS)
    self.image.save( outfile )

class Frames:
  def __init__( self, list_of_images = [] ):
    '''Loads up the meta data for each image'''
    self.images = []
    for fn in list_of_images:
      self.images.append( Frame(fn) )
    self.index = -1
    self.length = len(self.images)
    self.evaluate()
  def __len__(self):
    return self.length
  def __iter__(self):
    return self
  def __next__(self):
    if len(self.images) == 0:
      raise StopIteration
    self.index += 1
    if self.index < self.length:
      return self.images[self.index]
    raise StopIteration
  def __getitem__(self, item):
    return self.images[item]
  def print(self):
    for img in self.images:
      img.print_times()
  def evaluate(self):
    '''Evaluates the frames, calculating delta time between each.'''
    if self.length:
      tbeg = self.images[0].datetime_obj
      tend = self.images[-1].datetime_obj
      self.tspan = tend - tbeg
    for i in range(self.length):
      this = self.images[i]
      this.outfile = f'tmp/image{i:03d}.jpg'
      if i > 0:
        prev = self.images[i-1]
        this.timediff = this.datetime_obj - prev.datetime_obj
        this.tprogress = this.datetime_obj - tbeg
        this.tprogress_frac = this.tprogress / self.tspan
        this.tprogress_hours = int( this.tprogress.total_seconds()/3600 + 0.5 )

def make_images():
  for img in frames:
    img.print()
    img.load()
    img.timeline()
    img.save()

def make_movie():
  try:
    os.remove(filename_movie)
  except OSError:
    pass
  stream = ffmpeg.input('tmp/image*.jpg', pattern_type='glob',
                        framerate=0.5)
  stream = ffmpeg.output(stream, filename_movie)
  ffmpeg.run(stream)

frames = Frames(list_of_images)
def main():
  # for testing
  f1 = frames[0]
  f2 = frames[1]
  f1.load()
  make_images()
  make_movie()


if __name__ == '__main__':
  main()
