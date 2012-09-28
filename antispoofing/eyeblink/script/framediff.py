#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.anjos@idiap.ch>
# Mon 02 Aug 2010 11:31:31 CEST

"""Calculates the normalized frame differences for eye regions, for all videos
of the REPLAY-ATTACK database. A basic variant of this technique is described
on the paper: Counter-Measures to Photo Attacks in Face Recognition: a public
database and a baseline, Anjos & Marcel, IJCB'11.
"""

import os, sys
import argparse

def main():

  import bob
  import numpy
  from xbob.db.replay import Database

  protocols = [k.name for k in Database().protocols()]

  basedir = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))
  INPUTDIR = os.path.join(basedir, 'database')
  ANNOTATIONS = os.path.join(basedir, 'annotations')
  OUTPUTDIR = os.path.join(basedir, 'framediff')

  parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('inputdir', metavar='DIR', type=str, default=INPUTDIR,
      nargs='?', help='Base directory containing the videos to be treated by this procedure (defaults to "%(default)s")')
  parser.add_argument('annotations', metavar='DIR', type=str,
      default=ANNOTATIONS, nargs='?', help='Base directory containing the (flandmark) annotations to be treated by this procedure (defaults to "%(default)s")')
  parser.add_argument('outputdir', metavar='DIR', type=str, default=OUTPUTDIR,
      nargs='?', help='Base output directory for every file created by this procedure defaults to "%(default)s")')
  parser.add_argument('-p', '--protocol', metavar='PROTOCOL', type=str,
      default='grandtest', choices=protocols, dest="protocol",
      help='The protocol type may be specified instead of the the id switch to subselect a smaller number of files to operate on (one of "%s"; defaults to "%%(default)s")' % '|'.join(sorted(protocols)))
  parser.add_argument('-M', '--maximum-displacement', metavar='FLOAT',
      type=float, dest="max_displacement", default=0.2, help="Maximum displacement (w.r.t. to the eye width) between eye-centers to consider the eye for calculating eye-differences (defaults to %(default)s)")

  supports = ('fixed', 'hand', 'hand+fixed')

  parser.add_argument('-s', '--support', metavar='SUPPORT', type=str,
      default='hand+fixed', dest='support', choices=supports, help="If you would like to select a specific support to be used, use this option (one of '%s'; defaults to '%%(default)s')" % '|'.join(sorted(supports)))

  # The next option just returns the total number of cases we will be running
  # It can be used to set jman --array option.
  parser.add_argument('--grid-count', dest='grid_count', action='store_true',
      default=False, help=argparse.SUPPRESS)

  args = parser.parse_args()

  if args.support == 'hand+fixed': args.support = ('hand', 'fixed')

  from .. import utils 

  db = Database()

  process = db.objects(protocol=args.protocol, support=args.support,
      cls=('real', 'attack', 'enroll'))

  if args.grid_count:
    print len(process)
    sys.exit(0)

  # if we are on a grid environment, just find what I have to process.
  if os.environ.has_key('SGE_TASK_ID'):
    key = int(os.environ['SGE_TASK_ID']) - 1
    if key >= len(process):
      raise RuntimeError, "Grid request for job %d on a setup with %d jobs" % \
          (key, len(process))
    process = [process[key]]

  for counter, obj in enumerate(process):

    filename = str(obj.videofile(args.inputdir))
    input = bob.io.VideoReader(filename)
    annotations = utils.flandmark_load_annotations(obj, args.annotations,
        verbose=True)

    sys.stdout.write("Processing file %s (%d frames) [%d/%d]..." % (filename,
      input.number_of_frames, counter+1, len(process)))

    # start the work here...
    frames = [bob.ip.rgb_to_gray(k) for k in input]
    #utils.light_normalize_tantriggs(frames, annotations, 0, len(frames))
    utils.light_normalize_histogram(frames, annotations, 0, len(frames))

    features = numpy.ndarray((input.number_of_frames, 2), dtype='float64')
    features[:] = numpy.NaN

    for k in range(1, len(frames)):

      curr_annot = annotations[k] if annotations.has_key(k) else None
      prev_annot = annotations[k-1] if annotations.has_key(k-1) else None
      use_annotation = (prev_annot, curr_annot)

      use_frames = (frames[k-1], frames[k])

      # maximum of 5 pixel displacement acceptable
      eye_diff, eye_pixels = utils.eval_eyes_difference(use_frames, 
          use_annotation, args.max_displacement)
      facerem_diff, facerem_pixels = utils.eval_face_remainder_difference(
          use_frames, use_annotation, eye_diff, eye_pixels)

      if eye_pixels != 0:
        features[k][0] = eye_diff/float(eye_pixels)
      else: 
        features[k][0] = 0.

      if facerem_pixels != 0:
        features[k][1] = facerem_diff/float(facerem_pixels)
      else: 
        features[k][1] = 1.

      if eye_diff == 0: sys.stdout.write('x')
      else: sys.stdout.write('.')
      sys.stdout.flush()

    obj.save(features, directory=args.outputdir, extension='.hdf5')

    sys.stdout.write('\n')
    sys.stdout.flush()

  return 0
