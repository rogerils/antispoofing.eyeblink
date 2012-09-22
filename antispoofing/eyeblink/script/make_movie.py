#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.anjos@idiap.ch>
# Tue 05 Apr 2011 13:37:31 CEST 

"""Creates a movie showing how the input data evolves with the original video.
"""

import os
import sys
import numpy
import argparse
import matplotlib.pyplot as mpl
from matplotlib.cm import gray as GrayColorMap
import bob

LABEL = ('Full Scene', 'Face only', 'Background', 'Eyes only', 'Face reminder')
COLOR = ('black', 'red', 'blue', 'green', 'magenta')
basedir = 'bindata'

def fig2array(fig):
  """Converts a Matplotlib figure to a 3D array with RGB channels
  
  Keyword parameters:
  
  fig 
    a matplotlib figure

  Returns a 3D array of RGB values (arranged by planes as Bob likes it)
  """

  # draw the renderer
  fig.canvas.draw()

  # Get the RGB buffer from the figure, re-shape it adequately
  w,h = fig.canvas.get_width_height()
  buf = numpy.fromstring(fig.canvas.tostring_rgb(),dtype=numpy.uint8)
  buf.shape = (h,w,3)
  return numpy.transpose(buf, (2,0,1))

def main():
  
  import os, sys
  from xbob.db.replay import Database

  parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('path', metavar='PATH', type=str, 
      help='Base path to the file you need plotting')
  parser.add_argument('features', metavar='DIR', type=str,
      help='Base input directory containing the features to be plotted')

  args = parser.parse_args()

  db = Database()

  # Gets the information concerning the input path or id
  info = db.info(db.reverse(parser.path,))[0]

  print "Movie: %s" % sys.argv[1]
  video = torch.database.VideoReader(sys.argv[1])
  
  # Choose the printed frames here.
  start = 1
  end = 225

  frames = tuple(video)[start:end]

  print "Feats: %s" % sys.argv[2]
  features = load_file(sys.argv[2])
  normed = values_normed(features, end, start)
  bg_normed = values_normed_by_background(features, end, start)
  normed_minus_top = max_values_normed_minus_running_base(features, end, start)
  normed_bg_minus_top = max_values_normed_minus_running_background(features, end, start)
  values = numpy.vstack((normed, bg_normed, normed_minus_top, normed_bg_minus_top))
  values = values.transpose()
  labels = ('Norm\'ed', 'Norm\'ed-Top')

  # plot N sequential images containing the video on the top and the advancing
  # graph of the features of choice on the bottom
  fig = mpl.figure()
  gray = torch.core.array.uint8_2(video.height, video.width)
  sys.stdout.write("Writing %d frames" % (end-start))
  sys.stdout.flush()
  outv = None #output video place holder
  orows, ocolumns = None, None #the size of every frame in outv
  for t in range(start,end):
    mpl.subplot(211)
    mpl.title("Frame %05d" % t)
    torch.ip.rgb_to_gray(frames[t-start], gray)
    mpl.imshow(gray, cmap=GrayColorMap) #top plot
    mpl.subplot(212)
    mpl.plot(numpy.arange(start, t+1), values[:t,:], label=labels) #bottom plot
    mpl.plot(numpy.arange(start, end), (end-start)*[float(sys.argv[3])],
        label="threshold") #threshold line
    mpl.axis((start, end, values.min(), values.max()))
    mpl.grid(True)
    mpl.xlabel("Frames")
    mpl.ylabel("Magnitude")
    figure = fig2bzarray(fig)
    if outv is None:
      orows = 2*(figure.extent(1)/2)
      ocolumns = 2*(figure.extent(2)/2)
      outv = torch.database.VideoWriter(sys.argv[4], orows, ocolumns,
          video.frameRate)
    outv.append(figure[:,0:orows,0:ocolumns])
    mpl.clf()
    sys.stdout.write('.')
    sys.stdout.flush()
  print ''
