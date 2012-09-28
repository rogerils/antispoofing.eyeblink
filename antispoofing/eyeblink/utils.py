#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.dos.anjos@gmail.com>
# Sat 22 Sep 18:34:40 2012 

"""General utilities for Eye-Blinking evaluation
"""

import numpy

def load_annotations(obj, dir, ext, verbose):
  """Loads annotations for the given object from the directory/extension given
  as input.

  Keyword parameters:

  obj
    The object, as returned by queries using
    ``xbob.db.replay.Database.objects``

  dir
    The directory where the annotations are supposed to be found

  ext
    The extension to be used for loading the annotations.

  verbose
    Loads the file and prints some stuff about it

  Returns a dictionary of annotations (key is the frame number, starting from
  0). Each dictionary value corresponds to another dictionary with 2 entries:

  bbox
    Contains a 4-tuple (integers) that define the bounding box in which the
    key-point localization took place (``x``, ``y``, ``width``, ``height``).

  landmark
    Contains a size-undefined tuple of 2-tuples for each localized key-point.
    The number of keypoints depends on the localization algorithm or annotation
    configuration used and must be interpreted accordingly.
  """

  from itertools import izip

  filename = obj.make_path(dir, ext)

  if verbose:
    print "Loading annotations from '%s'..." % filename,
  arr = [k.strip().split() for k in open(filename, 'rt')]
  if verbose:
    print "%d frames loaded" % len(arr)

  retval = {}

  for line in arr:
    key = int(line[0])
    bbx = [int(k) for k in line[1:5]]
    if bbx[2] < 50:
      if verbose:
        print "Annotation for frame %d was removed (width = %d is < 50)" % \
            (key, bbx[2])
      continue
    it = iter([int(k) for k in line[5:]])
    landmarks = izip(it, it) # pairwise assembly
    retval[key] = {'bbox': tuple(bbx), 'landmark': tuple(landmarks)}

  return retval

def light_normalize_tantriggs(frames, annotations, start, end):
  """Runs the light normalization on detected faces"""

  GAMMA = 0.2
  SIGMA0 = 1.
  SIGMA1 = 2.
  SIZE = 5
  THRESHOLD = 10.
  ALPHA = 0.1

  from bob.ip import TanTriggs
  from bob.core import convert

  op = TanTriggs(GAMMA, SIGMA0, SIGMA1, SIZE, THRESHOLD, ALPHA)

  counter = 0
  for key in range(start, end):
    if annotations.has_key(key):
      x, y, width, height = annotations[key]['face_remainder']
      res = op(frames[counter][y:(y+height), x:(x+width)])
      frames[counter][y:(y+height), x:(x+width)] = \
          convert(res, 'uint8', (0, 255), (-THRESHOLD, THRESHOLD))

    counter += 1

def light_normalize_histogram(frames, annotations, start, end):
  """Runs the light normalization on detected faces"""

  from bob.ip import histogram_equalization
  from bob.core import convert

  counter = 0
  for key in range(start, end):
    if annotations.has_key(key):
      x, y, width, height = annotations[key]['face_remainder']
      res = histogram_equalization(frames[counter][y:(y+height), x:(x+width)])
      frames[counter][y:(y+height), x:(x+width)] = res

    counter += 1

def flandmark_calculate_eye_region(annotations):
  """Increments each annotation with the eye-regions calculated taking into
  consideration the landmarks were extracted automatically using flandmark.
  
  This procedure adds a ``eyes`` key to the input dictionary, for each
  annotation. The new entry contains 2 4-tuples with the right and left eye
  bounding-boxes respectively. It also creates an new entry called
  ``eye_centers`` which contains 2-tuples with the estimated eye-centers for
  the right and left eyes respectively.
  """

  from scipy.spatial.distance import euclidean

  center, ic_reye, ic_leye, r_mouth, l_mouth, oc_reye, oc_leye, nose = \
      annotations['landmark']

  width_enlargement = 0.1 #bounding box width extra w.r.t. eye width
  height_proportion = 0.5 #bounding box height proportion w.r.t. eye width

  annotations['eye_centers'] = (
      (
        int(round( ( ic_reye[0] + oc_reye[0] ) / 2.0 )),
        int(round( ( ic_reye[1] + oc_reye[1] ) / 2.0 )),
      ),
      (
        int(round( ( ic_leye[0] + oc_leye[0] ) / 2.0 )),
        int(round( ( ic_leye[1] + oc_leye[1] ) / 2.0 )),
      ),
      )

  width = euclidean(ic_leye, oc_leye)
  x, y = ic_leye # note: left-eye is on the right at image
  bbox_leye = (
      x - ((width_enlargement * width)/2.0),
      y - ((height_proportion * width)/2.0),
      ( 1.0 + width_enlargement ) * width,
      height_proportion * width,
      )
  bbox_leye = [int(round(k)) for k in bbox_leye]

  width = euclidean(ic_reye, oc_reye)
  x, y = oc_reye # note: right-eye is on the left at image
  bbox_reye = (
      x - ((width_enlargement * width)/2.0),
      y - ((height_proportion * width)/2.0),
      ( 1.0 + width_enlargement ) * width,
      height_proportion * width,
      )
  bbox_reye = [int(round(k)) for k in bbox_reye]

  annotations['eyes'] = (bbox_reye, bbox_leye)

  return annotations['eyes']

def flandmark_calculate_face_remainder(annotations):
  """Increments each annotation with the face-remainder region calculated
  taking into consideration the landmarks were extracted automatically using
  flandmark.
  
  This procedure adds a ``face_remainder`` key to the input dictionary, for
  each annotation. The new entry contains a single 4-tuple with face remainder
  area.
  """

  from scipy.spatial.distance import euclidean

  center, ic_reye, ic_leye, r_mouth, l_mouth, oc_reye, oc_leye, nose = \
      annotations['landmark']

  width_enlargement = 0.3 #eye outer corner distance extra width
  nose_distance_proportion = 1.6 #eye -> nose height enlargement
  mouth_distance_proportion = 1.3 #nose -> mouth height enlargement

  width = euclidean(oc_reye, oc_leye)
  
  eye_center = (
      ( ic_leye[0] + ic_reye[0] ) / 2.0, 
      ( ic_leye[1] + ic_reye[1] ) / 2.0
      )

  nose_distance = euclidean(eye_center, nose)

  extra_on_right_side = width_enlargement * width / 2.0
  extra_on_top_side = nose_distance_proportion * nose_distance / 2.0
  top_left_x = oc_reye[0] - extra_on_right_side
  top_left_y = eye_center[1] - extra_on_top_side

  mouth_center = (
      ( r_mouth[0] + l_mouth[0] ) / 2.0,
      ( r_mouth[1] + l_mouth[1] ) / 2.0,
      )

  mouth_distance = euclidean(eye_center, mouth_center)
  height = extra_on_top_side + (mouth_distance_proportion * mouth_distance)

  bbox = (top_left_x, top_left_y, (1.0+width_enlargement)*width, height)
  bbox = [int(round(k)) for k in bbox]

  annotations['face_remainder'] = bbox

  return annotations['face_remainder']

def flandmark_load_annotations(obj, dir, verbose):
  """Loads annotations for the given object from the directory/extension given
  as input.

  Keyword parameters:

  obj
    The object, as returned by queries using
    ``xbob.db.replay.Database.objects``

  dir
    The directory where the annotations are supposed to be found

  verbose
    Loads the file and prints some stuff about it

  Returns a dictionary of annotations (key is the frame number, starting from
  0). Each dictionary value corresponds to another dictionary with 2 entries:

  bbox
    Contains a 4-tuple (integers) that define the bounding box in which the
    key-point localization took place (``x``, ``y``, ``width``, ``height``).

  landmark
    Contains a size-undefined tuple of 2-tuples for each localized key-point.
    The number of keypoints depends on the localization algorithm or annotation
    configuration used and must be interpreted accordingly.
  """

  retval = load_annotations(obj, dir, '.flandmark', verbose)
  for v in retval.itervalues(): flandmark_calculate_eye_region(v)
  for v in retval.itervalues(): flandmark_calculate_face_remainder(v)
  return retval

def select(arr, bbx):
  """Sub-selects a given area of the array, given the bounding-box.
  """
  x, y, width, height = bbx
  return arr[y:(y+height), x:(x+width)].astype('int32')

def diff(prev, curr, bbx):
  """Calculates the absolute pixel-by-pixel differences between to consecutive
  frames, given a bounding-box region of interest.
  """
  return abs(select(curr, bbx) - select(prev, bbx))

def eval_eyes_difference(frames, annotations, max_center_displacement):
  """Evaluates the normalized frame difference on the eye region

  If annotation is None or invalid, returns 0.

  Keyword Parameters:

  frames
    A tuple with two frames with which to calculate the frame differences. Both
    frames need to be gray-scaled

  annotations
    Annotations for the two frames (dictionaries with ``eyes`` field)

  max_center_displacement
    Maximum displacement between eye-centers to consider that particular eye
    in the calculation.
  """
  
  from scipy.spatial.distance import euclidean

  r = 0.
  pixels = 0

  previous, current = frames
  prev_annot, curr_annot = annotations

  if curr_annot and prev_annot:

    max_displacement = max_center_displacement * curr_annot['eyes'][0][2]
    displacement = euclidean(prev_annot['eye_centers'][0],
        curr_annot['eye_centers'][0])
    if displacement < max_displacement:
      d = diff(previous, current, curr_annot['eyes'][0])
      pixels += d.size
      r += d.sum()

    max_displacement = max_center_displacement * curr_annot['eyes'][1][2]
    displacement = euclidean(prev_annot['eye_centers'][1], 
      curr_annot['eye_centers'][1])
    if displacement < max_displacement:
      d = diff(previous, current, curr_annot['eyes'][1])
      pixels += d.size
      r += d.sum()
    
  return r, pixels

def eval_face_remainder_difference(frames, annotations, eye_diff, eye_pixels):
  """Evaluates the normalized frame difference on the face remainder

  If annotation is None or invalid, returns 0

  frames
    A tuple with two frames with which to calculate the frame differences. Both
    frames need to be gray-scaled

  annotations
    Annotation for the current frame (dictionary with ``eyes`` and
    ``face_remainder`` fields)

  eye_diff
    The difference in the eyes regions

  eye_pixels
    The total number of pixels in the eye region.
  """
  
  previous, current = frames
  prev_annot, curr_annot = annotations

  if prev_annot and curr_annot:

    face = diff(previous, current, curr_annot['face_remainder'])
    remainder = face.sum() - eye_diff
    remainder_size = face.size - eye_pixels

    if remainder < 0:
      raise RuntimeError, "Remainder is smaller than zero"

    # FIXME: this is not as good as calculating intersecting areas of all
    # rectangles involved in this operation.
    return remainder, remainder_size

  return 0, 0 

def rmean(arr):
  """Calculates the running mean in a 1D numpy array"""
  return numpy.array([numpy.mean(arr[:(k+1)]) for k in range(len(arr))])

def rstd(arr):
  """Calculates the running standard deviation (biased estimator) in a 1D numpy array"""
  return numpy.array([numpy.std(arr[:(k+1)]) for k in range(len(arr))])

def score(data):
  '''Calculates the score in any given input frame.
  
  S = ratio(eye/face_rem) - running_average(ratio(eye/face_rem))

  The final score is set to S, unless any of the following conditions are met:

  1
    S < running_std_deviation(ratio(...))

  2
    eye == 0

  3
    S < running_average(ratio(...))

  In these cases S is replaced by the output of running_average(ratio(...)).
  '''

  def replace_nan(nparr):
    """If the value is close to zero, set it to a default"""
    nparr[numpy.isnan(nparr)] = 0
    return nparr

  denominator = numpy.copy(data[:,1])
  denominator[denominator == 0.0] = 1.0

  norm = replace_nan(data[:,0]/denominator)
  rm = rmean(norm)
  rs = rstd(norm)
  retval = norm - rm
  retval[data[:,0] == 0.0] = rm[data[:,0] == 0.0]
  retval[abs(retval) < rs] = rm[abs(retval) < rs]
  retval[retval < rm] = rm[retval < rm]
  return retval
  
def count_blinks(scores, std_thres, skip_frames):
  """Tells the client has blinked
  
  Keyword arguments

  scores
    The score set to be analyzed

  std_thres
    The threshold applied on the current point being analized in the scores
    to check for valid blinks (in number of standard deviations from the
    running average).

  skip_frames
    How many frames to skip before start eye-blink detection again (after an
    eye-blink has been successfuly detected). This is required to avoid the
    method to falsely detect positives following a successful detection.
  """

  detected = 0
  skip = skip_frames #start by skipping the initial frames
  rm = rmean(scores)
  rs = rstd(scores)
  retval = numpy.ndarray((len(scores),), dtype='float64')

  for k, score in enumerate(scores):
    if skip:
      skip -= 1
      retval[k] = detected
      continue

    if (score-rm[k]) >= (std_thres * rs[k]):
      detected += 1
      skip = skip_frames

    retval[k] = detected

  return retval
