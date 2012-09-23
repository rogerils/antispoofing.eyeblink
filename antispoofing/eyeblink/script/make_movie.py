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
  parser.add_argument('-M', '--maximum-displacement', metavar='FLOAT',
      type=float, dest="max_displacement", default=0.2, help="Maximum displacement (w.r.t. to the eye width) between eye-centers to consider the eye for calculating eye-differences")
  parser.add_argument('-S', '--skip-frames', metavar='INT', type=int,
      default=10, dest='skip', help="Number of frames to skip once an eye-blink has been detected (defaults to %(default)s)")
  parser.add_argument('-T', '--threshold-ratio', metavar='FLOAT', type=float,
      default=3.0, dest='thres_ratio', help="How many standard deviations to use for counting positive blink picks to %(default)s)")

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

  # Loads the input video
  frames = [bob.ip.rgb_to_gray(k) for k in video[start:end]]

  # Recalculates the features
  annotations = utils.flandmark_load_annotations(obj, args.annotations,
      verbose=True)

  # Light-normalizes detected faces
  #utils.light_normalize_tantriggs(frames, annotations, start, end)
  utils.light_normalize_histogram(frames, annotations, start, end)

  features = numpy.zeros((len(frames), 2), dtype='float64')

  sys.stdout.write("Computing features ")
  sys.stdout.flush()
  for k in range(start+1, end):
    curr_annot = annotations[k] if annotations.has_key(k) else None
    prev_annot = annotations[k-1] if annotations.has_key(k-1) else None
    use_annotation = (prev_annot, curr_annot)
    use_frames = (frames[k-1], frames[k])

    # maximum of 5 pixel displacement acceptable
    eye_diff, eye_pixels = utils.eval_eyes_difference(use_frames, 
        use_annotation, max_center_displacement=args.max_displacement)
    facerem_diff, facerem_pixels = utils.eval_face_remainder_difference(
        use_frames, use_annotation, eye_diff, eye_pixels)

    if eye_pixels != 0: features[k][0] = eye_diff/float(eye_pixels)
    else: features[k][0] = 0.

    if facerem_pixels != 0: features[k][1] = facerem_diff/float(facerem_pixels)
    else: features[k][1] = 1.

    if eye_diff == 0: sys.stdout.write('x')
    else: sys.stdout.write('.')
    sys.stdout.flush()

  scores = utils.score(features)

  sys.stdout.write('\n')
  sys.stdout.flush()

  # plot N sequential images containing the video on the top and the advancing
  # graph of the features of choice on the bottom
  fig = mpl.figure()
  sys.stdout.write("Writing %d frames " % (end-start))
  sys.stdout.flush()

  outv = None #output video place holder
  orows, ocolumns = None, None #the size of every frame in outv
  old_blinks = 0
  
  for k in range(start,end):

    mpl.subplot(211)
    mpl.title("Frame %05d" % k)

    use_annotation = annotations[k] if annotations.has_key(k) else None
    
    if use_annotation:
      x, y, width, height = use_annotation['bbox']
      bob.ip.draw_box(frames[k], x, y, width, height, 255)
      x, y, width, height = use_annotation['eyes'][0]
      bob.ip.draw_box(frames[k], x, y, width, height, 255)
      x, y, width, height = use_annotation['eyes'][1]
      bob.ip.draw_box(frames[k], x, y, width, height, 255)
      x, y, width, height = use_annotation['face_remainder']
      bob.ip.draw_box(frames[k], x, y, width, height, 255)

    mpl.imshow(frames[k], cmap=GrayColorMap) #top plot

    mpl.subplot(212)

    score_set = scores[start:k+1]
    blinks = utils.count_blinks(score_set, args.thres_ratio, args.skip)
    rmean = utils.rmean(score_set)[-1]
    rstd = utils.rstd(score_set)[-1]
    threshold = (args.thres_ratio * rstd) + rmean

    mpl.plot(numpy.arange(start, k+1), score_set, linewidth=2, label='score')
    mpl.hlines(rmean, start, end, color='red', 
        linestyles='dashed', alpha=0.8, label='mean')
    mpl.hlines(threshold, start, end, color='red', 
        linestyles='solid', alpha=0.8, label='threshold')
    yrange = scores.max() - scores.min()
    mpl.axis((start, end, scores.min(), (0.2*yrange) + scores.max()))
    mpl.grid(True)
    mpl.xlabel("Frames | Blinks = %d" % blinks)
    mpl.ylabel("Magnitude")

    figure = fig2array(fig)

    if outv is None:
      orows = 2*(figure.shape[1]/2)
      ocolumns = 2*(figure.shape[2]/2)
      outv = bob.io.VideoWriter(args.output, orows, ocolumns, video.frame_rate)

    outv.append(figure[:,0:orows,0:ocolumns])
    mpl.clf()
    if blinks != old_blinks:
      old_blinks = blinks
      sys.stdout.write('%d' % old_blinks)
    else:
      sys.stdout.write('.')
    sys.stdout.flush()

  sys.stdout.write('\n')
