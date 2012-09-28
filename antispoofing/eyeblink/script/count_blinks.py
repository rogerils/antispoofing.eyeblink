#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.anjos@idiap.ch>
# Sun 09 Sep 2012 12:42:38 CEST 

"""Count blinks given partial scores.
"""

import os
import sys
import bob
import numpy
import argparse

def main():
  """Main method"""
  
  from xbob.db.replay import Database
  from .. import utils

  protocols = [k.name for k in Database().protocols()]

  parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('inputdir', metavar='DIR', type=str, help='Base directory containing the scores to be loaded and merged')
  parser.add_argument('outputdir', metavar='DIR', type=str, help='Base output directory for every file created by this procedure')
  
  parser.add_argument('-p', '--protocol', metavar='PROTOCOL', type=str,
      default='grandtest', choices=protocols, dest="protocol",
      help="The protocol type may be specified to subselect a smaller number of files to operate on (one of '%s'; defaults to '%%(default)s')" % '|'.join(sorted(protocols)))

  supports = ('fixed', 'hand', 'hand+fixed')

  parser.add_argument('-s', '--support', metavar='SUPPORT', type=str, 
      default='hand+fixed', dest='support', choices=supports, help="If you would like to select a specific support to be used, use this option (one of '%s'; defaults to '%%(default)s')" % '|'.join(sorted(supports))) 

  parser.add_argument('-S', '--skip-frames', metavar='INT', type=int,
      default=10, dest='skip', help="Number of frames to skip once an eye-blink has been detected (defaults to %(default)s)")

  parser.add_argument('-T', '--threshold-ratio', metavar='FLOAT', type=float,
      default=3.0, dest='thres_ratio', help="How many standard deviations to use for counting positive blink picks to %(default)s)")

  parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
      default=False, help='Increases this script verbosity')

  args = parser.parse_args()

  if not os.path.exists(args.inputdir):
    parser.error("input directory `%s' does not exist" % args.inputdir)

  if args.support == 'hand+fixed': args.support = ('hand', 'fixed')

  if not os.path.exists(args.outputdir):
    if args.verbose: print "Creating output directory %s..." % args.outputdir
    os.makedirs(args.outputdir)

  db = Database()

  objs = db.objects(protocol=args.protocol, support=args.support,
      cls=('real', 'attack', 'enroll'))

  counter = 0
  for obj in objs:
    counter += 1
    arr = obj.load(args.inputdir, '.hdf5')
    nb = utils.count_blinks(arr, args.thres_ratio, args.skip)

    if args.verbose:
      print "Processed file %s [%d/%d]... %d blink(s)" % \
          (obj.path, counter, len(objs), nb[-1])

    obj.save(nb, args.outputdir, '.hdf5')
