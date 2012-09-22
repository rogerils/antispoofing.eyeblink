#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.dos.anjos@gmail.com>
# Sat 22 Sep 18:34:40 2012 

"""General utilities for Eye-Blinking evaluation
"""

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
  from numpy import loadtxt

  filename = obj.make_path(dir, ext)

  if verbose:
    print "Loading annotations from '%s'..." % filename,
  arr = loadtxt(filename, dtype=int)
  if verbose:
    print "%d frames loaded" % len(arr)

  retval = {}

  for line in arr:
    key = line[0]
    bbx = [int(k) for k in line[1:5]]
    if bbx[2] < 50:
      if verbose:
        print "Annotation for frame %d was removed (width = %d is < 50)" % \
            (key, bbox[2])
      continue
    it = iter([int(k) for k in line[5:]])
    landmarks = izip(it, it) # pairwise assembly
    retval[key] = {'bbox': tuple(bbx), 'landmark': tuple(landmarks)}

  return retval

def flandmark_calculate_eye_region(annotations):
  """Increments each annotation with the eye-regions calculated taking into
  consideration the landmarks were extracted automatically using flandmark.
  
  This procedure adds a ``eyes`` key to the input dictionary, for each
  annotation. The new entry contains 2 4-tuples with the right and left eye
  bounding-boxes respectively.
  """

  from scipy.spatial.distance import euclidean

  center, ic_reye, ic_leye, r_mouth, l_mouth, oc_reye, oc_leye, nose = \
      annotations['landmark']

  width_enlargement = 0.3 #in each side of the eye
  nose_distance_proportion = 1.0 #bounding box height proportion

  eye_center = (
      ( ic_leye[0] + ic_reye[0] ) / 2.0, 
      ( ic_leye[1] + ic_reye[1] ) / 2.0
      )

  nose_distance = euclidean(eye_center, nose)

  width = euclidean(ic_leye, oc_leye)
  x, y = ic_leye # note: left-eye is on the right at image
  bbox_leye = (
      x - (width_enlargement * width), 
      y - (nose_distance_proportion * nose_distance / 2.0),
      ( 1.0 + ( 2 * width_enlargement ) ) * width,
      nose_distance_proportion * nose_distance
      )
  bbox_leye = [int(round(k)) for k in bbox_leye]

  width = euclidean(ic_reye, oc_reye)
  x, y = oc_reye # note: right-eye is on the left at image
  bbox_reye = (
      x - (width_enlargement * width), 
      y - (nose_distance_proportion * nose_distance / 2.0),
      ( 1.0 + ( 2 * width_enlargement ) ) * width,
      nose_distance_proportion * nose_distance
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
  return arr[y:(y+height), x:(x+width)]

def diff(prev, curr, bbx):
  """Calculates the absolute pixel-by-pixel differences between to consecutive
  frames, given a bounding-box region of interest.
  """
  return abs(
      select(curr, bbx).astype('int32') - select(prev, bbx).astype('int32')
      )

def eval_eyes_difference(previous, current, annotation):
  """Evaluates the normalized frame difference on the eye region

  If annotation is None or invalid, returns 0

  Keyword Parameters:

  previous
    Previous frame as a gray-scaled image

  current
    The current frame as a gray-scaled image

  annotation
    Annotation for the current frame (dictionary with ``eyes`` field)
  """

  r = 0.

  if annotation:

    r_eye, l_eye = annotation['eyes']
    r = ( diff(previous, current, r_eye).mean() + \
          diff(previous, current, l_eye).mean() ) / 2.

  return r

def eval_face_remainder_difference(previous, current, annotation):
  """Evaluates the normalized frame difference on the face remainder

  If annotation is None or invalid, returns 0

  previous
    Previous frame as a gray-scaled image

  current
    The current frame as a gray-scaled image

  annotation
    Annotation for the current frame (dictionary with ``eyes`` and
    ``face_remainder`` fields)
  """
  
  r = 0.

  if annotation:

    face = diff(previous, current, annotation['face_remainder'])
    r_eye = diff(previous, current, annotation['eyes'][0])
    l_eye = diff(previous, current, annotation['eyes'][1])
    remainder = face.sum() - (r_eye.sum() + l_eye.sum())
    remainder_size = face.size  - (r_eye.size + l_eye.size)

    # FIXME: this is not as good as calculating intersecting areas of all
    # rectangles involved in this operation.
    r = abs(remainder / float(remainder_size))

  return r
