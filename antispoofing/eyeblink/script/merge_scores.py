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
  from .. import utils

  protocols = [k.name for k in Database().protos()]

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

  def write_file(group):

    if args.verbose:
      print "Processing '%s' group..." % group
  
    out = open(os.path.join(args.outputdir, '%s-5col.txt' % group), 'wt')

    reals = db.objects(protocol=args.protocol, support=args.support,
        groups=(group,), cls=('real',))
    attacks = db.objects(protocol=args.protocol, support=args.support,
        groups=(group,), cls=('attack',))
    total = len(reals) + len(attacks)

    counter = 0
    positives = []
    for obj in reals:
      counter += 1
      fname = obj.make_path(args.inputdir, '.hdf5')

      if args.verbose: 
        print "Processing file %s [%d/%d]..." % (fname, counter, total)

      arr = bob.io.load(fname)

      nb = utils.count_blinks(arr[:args.end], args.thres_ratio, args.skip)
      positives.append(nb)
      
      out.write('%d %d %d %s %d\n' % (obj.client.id, obj.client.id, obj.client.id, obj.path, nb))

    negatives = []
    for obj in attacks:
      counter += 1
      fname = obj.make_path(args.inputdir, '.hdf5')

      if args.verbose: 
        print "Processing file %s [%d/%d]..." % (fname, counter, total)

      arr = bob.io.load(fname)

      nb = utils.count_blinks(arr[:args.end], args.thres_ratio, args.skip)
      negatives.append(nb)
      
      out.write('%d %d attack %s %d\n' % (obj.client.id, obj.client.id, obj.path, nb))

    out.close()

    return negatives, positives

  train_neg, train_pos = write_file('train')
  dev_neg, dev_pos = write_file('devel')
  test_neg, test_pos = write_file('test')

  def eval(nb):

    thres = nb - 0.5

    dev_far, dev_frr = bob.measure.farfrr(dev_neg, dev_pos, thres)
    dev_hter = (dev_far + dev_frr)/2.0

    test_far, test_frr = bob.measure.farfrr(test_neg, test_pos, thres)
    test_hter = (test_far + test_frr)/2.0

    print("Threshold = %d blink(s)" % nb)
    
    dev_ni = len(dev_neg) #number of impostors
    dev_fa = int(round(dev_far*dev_ni)) #number of false accepts
    dev_nc = len(dev_pos) #number of clients
    dev_fr = int(round(dev_frr*dev_nc)) #number of false rejects
    test_ni = len(test_neg) #number of impostors
    test_fa = int(round(test_far*test_ni)) #number of false accepts
    test_nc = len(test_pos) #number of clients
    test_fr = int(round(test_frr*test_nc)) #number of false rejects

    print " Error (devel): FAR %.2f%% (%d/%d) x FRR %.2f%% (%d/%d) = HTER %.2f%%" % \
        (100*dev_far, dev_fa, dev_ni, 100*dev_frr, dev_fr, dev_nc, 100*dev_hter)
    print " Error (test ): FAR %.2f%% (%d/%d) x FRR %.2f%% (%d/%d) = HTER %.2f%%" % \
        (100*test_far, test_fa, test_ni, 100*test_frr, test_fr, test_nc, 100*test_hter)

  eval(1)
  eval(2)
  eval(3)
