#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.anjos@idiap.ch>
# Sun 09 Sep 2012 12:42:38 CEST 

"""Merge multiple scores in score files and produce 5-column text files for the
whole database. Every line in the 5-column output file represents 1 video in
the database. Scores for every video are averaged according to options given to
this script before set in the output file.
"""

import os
import sys
import bob
import numpy
import argparse

def main():
  """Main method"""
  
  from xbob.db.replay import Database

  protocols = Database().protocols()

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

  parser.add_argument('-n', '--number-of-scores', metavar='INT', type=int,
      default=220, dest='end', help="Number of scores to merge from every file (defaults to %(default)s)")

  parser.add_argument('-S', '--skip-frames', metavar='INT', type=int,
      default=5, dest='skip', help="Number of frames to skip once an eye-blink has been detected (defaults to %(default)s)")

  parser.add_argument('-T', '--threshold-ratio', metavar='FLOAT', type=float,
      default=0.5, dest='thres_ratio', help="Ratio between the maximum score average and the score average used to calculate the blink detection threshold on (defaults to %(default)s)")

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

  def eval_blink_threshold():
    """Evaluates the blink threshold using the training set/photo protocol"""

    if args.verbose:
      print "Evaluating blink threshold using 'train/photo/real-access' group..."
    
    avg = []
    max = []
    
    data = db.files(protocol='photo', groups='train', cls='real')

    for key, value in data.iteritems():
      fname = os.path.join(args.inputdir, value + '.hdf5')
      scores = bob.io.load(fname)
      avg.append(numpy.mean(scores))
      max.append(numpy.max(scores))

    avg = numpy.mean(avg)
    max = numpy.mean(max)

    # half-way between the average and the maximum
    retval = args.thres_ratio*(max - avg) + avg

    if args.verbose:
      print "Blink threshold set to %.5e" % retval

    return retval

  def count_blinks(scores, threshold, skip_frames):
    """Tells the client has blinked
    
    Keyword arguments

    scores
      The score set to be analyzed

    threshold
      The threshold to be used for checking blinks

    skip_frames
      How many frames to skip before start eye-blink detection again (after an
      eye-blink has been successfuly detected). This is required to avoid the
      method to falsely detect positives following a successful detection.
    """

    detected = 0
    skip = skip_frames #start by skipping the initial frames

    for score in scores:
      if skip:
        skip -= 1
        continue

      if score >= threshold:
        detected += 1
        skip = skip_frames

    return detected

  def write_file(group, threshold):

    if args.verbose:
      print "Processing '%s' group..." % group
  
    out = open(os.path.join(args.outputdir, '%s-5col.txt' % group), 'wt')

    reals = db.files(protocol=args.protocol, support=args.support,
        groups=(group,), cls=('real',))
    attacks = db.files(protocol=args.protocol, support=args.support,
        groups=(group,), cls=('attack',))
    total = len(reals) + len(attacks)

    counter = 0
    for key, value in reals.iteritems():
      counter += 1
      fname = os.path.join(args.inputdir, value + '.hdf5')

      if args.verbose: 
        print "Processing file %s [%d/%d]..." % (fname, counter, total)

      arr = bob.io.load(fname)

      nb = count_blinks(arr[:args.end], threshold, skip_frames=args.skip)
      
      # finds the client id
      client_id = int([k for k in os.path.basename(value).split('_') if k.find('client') == 0][0].replace('client', '').lstrip('0'))

      out.write('%d %d %d %s %d\n' % (client_id, client_id, client_id, value, nb))

    for key, value in attacks.iteritems():
      counter += 1
      fname = os.path.join(args.inputdir, value + '.hdf5')

      if args.verbose: 
        print "Processing file %s [%d/%d]..." % (fname, counter, total)

      arr = bob.io.load(fname)
      nb = count_blinks(arr[:args.end], threshold, skip_frames=args.skip)
      
      # finds the client id
      client_id = int([k for k in os.path.basename(value).split('_') if k.find('client') == 0][0].replace('client', '').lstrip('0'))

      out.write('%d %d attack %s %d\n' % (client_id, client_id, value, nb))

    out.close()

  threshold = eval_blink_threshold()
  write_file('train', threshold)
  write_file('devel', threshold)
  write_file('test', threshold)
