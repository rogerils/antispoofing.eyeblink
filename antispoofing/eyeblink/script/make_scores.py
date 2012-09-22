#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.anjos@idiap.ch>
# Thu 28 Jul 2011 14:18:23 CEST 

"""This script will run feature vectors through a simple algorithm that
computes a feature that indicates if the user eye has blinked.
"""

import os
import sys
import bob
import numpy
import argparse

def rmean(arr):
  """Calculates the running mean in a 1D numpy array"""
  return numpy.array([numpy.mean(arr[:(k+1)]) for k in range(len(arr))])

def score(data, average):
  '''Calculates the score in any given input frame.
  
  S = ratio(eye/face_rem) - 2 * running_average(ratio(eye/face_rem))
  '''

  def replace_nan(nparr):
    """If the value is close to zero, set it to a default"""
    nparr[numpy.isnan(nparr)] = 0
    return nparr

  norm = replace_nan(data[:,0]/data[:,1])
  #return norm - (2 * rmean(norm))
  return norm - average

def main():
  """Main method"""
  
  from xbob.db.replay import Database
  protocols = Database().protocols()

  basedir = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))

  INPUTDIR = os.path.join(basedir, 'framediff')
  OUTPUTDIR = os.path.join(basedir, 'scores')

  parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('inputdir', metavar='DIR', type=str, default=INPUTDIR,
      nargs='?', help='Base directory containing the frame differences that will be used to produce the scores (defaults to "%(default)s").')
  parser.add_argument('outputdir', metavar='DIR', type=str, default=OUTPUTDIR, nargs='?', help='Base directory that will be used to save the results (defaults to "%(default)s").')
  parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
      default=False, help='Increases this script verbosity')
  parser.add_argument('-p', '--protocol', metavar='PROTOCOL', type=str,
      default='grandtest', choices=protocols, dest="protocol",
      help="The protocol type may be specified to subselect a smaller number of files to operate on (one of '%s'; defaults to '%%(default)s')" % '|'.join(sorted(protocols)))

  supports = ('fixed', 'hand', 'hand+fixed')

  parser.add_argument('-s', '--support', metavar='SUPPORT', type=str,
      default='hand+fixed', dest='support', choices=supports, help="If you would like to select a specific support to be used, use this option (one of '%s'; defaults to '%%(default)s')" % '|'.join(sorted(supports)))

  args = parser.parse_args()

  if not os.path.exists(args.inputdir):
    parser.error("input directory `%s' does not exist" % args.inputdir)

  if not os.path.exists(args.outputdir):
    if args.verbose: print "Creating output directory `%s'..." % args.outputdir
    bob.db.utils.makedirs_safe(args.outputdir)

  if args.support == 'hand+fixed': args.support = ('hand', 'fixed')

  db = Database()

  # evaluates averages:
  averages = {}
  for client in db.clients():
    data = db.files(directory=args.inputdir, cls='enroll', clients=client,
        extension='.hdf5')

    partial = []
    for key, value in data.iteritems():
      scores = bob.io.load(value)
      partial.append(numpy.mean(scores))
    averages[client] = numpy.mean(partial)
    if args.verbose:
      sys.stdout.write('Average for client %d is %.5e\n' % (client,
        averages[client]))
      sys.stdout.flush()

  process = db.files(args.inputdir, extension='.hdf5', 
      protocol=args.protocol, support=args.support,
      cls=('real', 'attack', 'enroll'))

  counter = 0
  for key, filename in process.items():
    counter += 1
     
    filename = os.path.expanduser(filename)
    
    if args.verbose: sys.stdout.write("Processing file %s [%d/%d] " % (filename, counter, len(process)))

    input = bob.io.load(filename)

    info = db.info((key,))[0]

    db.save_one(key, score(input, averages[info['client']]), 
        directory=args.outputdir, extension='.hdf5')

    if args.verbose:
      sys.stdout.write('Saving results to "%s"...\n' % args.outputdir)
      sys.stdout.flush()

  if args.verbose: print "All done, bye!"
 
if __name__ == '__main__':
  main()
