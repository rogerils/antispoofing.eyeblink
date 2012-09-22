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
import matplotlib
matplotlib.use('Agg')
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
  buf = numpy.fromstring(fig.canvas.tostring_rgb(), dtype=numpy.uint8)
  buf.shape = (h,w,3)
  return numpy.transpose(buf, (2,0,1))

def main():
  
  import os, sys
  from xbob.db.replay import Database, File
  from .. import utils

  basedir = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))
  ANNOTATIONS = os.path.join(basedir, 'annotations')
  FEATURES = os.path.join(basedir, 'framediff')

  parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('annotations', metavar='DIR', type=str,
      default=ANNOTATIONS, nargs='?', help='Base directory containing the (flandmark) annotations to be treated by this procedure (defaults to "%(default)s")')
  parser.add_argument('path', metavar='PATH', type=str,
      help='Base path to the movie file you need plotting')
  parser.add_argument('output', metavar='FILE', type=str,
      help='Name of the output file to save the video')

  args = parser.parse_args()

  db = Database()

  # Gets the information concerning the input path or id
  db.assert_validity()
  splitted = args.path.split(os.sep)
  k = [splitted.index(k) for k in splitted if k in \
      ('train', 'test', 'devel', 'enroll')][0]
  splitted[-1] = os.path.splitext(splitted[-1])[0]
  path_query = os.sep.join(splitted[k:])
  obj = db.session.query(File).filter(File.path == path_query).one()

  video = bob.io.VideoReader(args.path)
  print "Opened movie file %s (%d frames), id = %d" % \
      (args.path, len(video), obj.id)

  # Choose the printed frames here.
  start = 0
  end = 225

  # Loads the input vide
  frames = video[start:end]

  # Recalculates the features
  annotations = utils.flandmark_load_annotations(obj, args.annotations,
      verbose=True)
  prev = bob.ip.rgb_to_gray(frames[0])
  curr = numpy.empty_like(prev)
  features = numpy.zeros((len(frames), 2), dtype='float64')

  print "Computing features",
  for k in range(start, end):
    sys.stdout.write('.')
    sys.stdout.flush()
    bob.ip.rgb_to_gray(frames[k], curr)
    use_annotation = annotations[k] if annotations.has_key(k) else None
    features[k][0] = utils.eval_eyes_difference(prev, curr, use_annotation)
    features[k][1] = utils.eval_face_remainder_difference(prev, curr, use_annotation)
    # swap buffers: curr <=> prev
    tmp = prev
    prev = curr
    curr = tmp

  sys.stdout.write('\n')
  sys.stdout.flush()

  labels = ('eyes', 'rem.')
  
  # plot N sequential images containing the video on the top and the advancing
  # graph of the features of choice on the bottom
  fig = mpl.figure()
  sys.stdout.write("Writing %d frames" % (end-start))
  sys.stdout.flush()

  outv = None #output video place holder
  orows, ocolumns = None, None #the size of every frame in outv
  gray = numpy.ndarray((video.height, video.width), dtype='uint8')
  
  for t in range(start,end):

    mpl.subplot(211)
    mpl.title("Frame %05d" % t)

    use_annotation = annotations[k] if annotations.has_key(k) else None
    
    bob.ip.rgb_to_gray(frames[t-start], gray)

    if use_annotation:
      x, y, width, height = use_annotation['bbox']
      bob.ip.draw_box(gray, x, y, width, height, 255)
      x, y, width, height = use_annotation['eyes'][0]
      bob.ip.draw_box(gray, x, y, width, height, 255)
      x, y, width, height = use_annotation['eyes'][1]
      bob.ip.draw_box(gray, x, y, width, height, 255)
      x, y, width, height = use_annotation['face_remainder']
      bob.ip.draw_box(gray, x, y, width, height, 255)

    mpl.imshow(gray, cmap=GrayColorMap) #top plot

    mpl.subplot(212)

    mpl.plot(numpy.arange(start, t+1), features[start:(t+1),:], label=labels)
    mpl.axis((start, end, features.min(), features.max()))
    mpl.grid(True)
    mpl.xlabel("Frames")
    mpl.ylabel("Magnitude")

    figure = fig2array(fig)

    if outv is None:
      orows = 2*(figure.shape[1]/2)
      ocolumns = 2*(figure.shape[2]/2)
      outv = bob.io.VideoWriter(args.output, orows, ocolumns, video.frame_rate)

    outv.append(figure[:,0:orows,0:ocolumns])
    mpl.clf()
    sys.stdout.write('.')
    sys.stdout.flush()

  sys.stdout.write('\n')
