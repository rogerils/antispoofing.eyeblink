================================================
 Eye-Blink Detector to Counter Spoofing Attacks
================================================

This package implements an eye-blink detector using a similar frame-differences
technique as described at the paper `Counter-Measures to Photo
Attacks in Face Recognition: a public database and a baseline`, by Anjos and
Marcel, International Joint Conference on Biometrics, 2011.

If you use this package and/or its results, please cite the following
publications:

1. The original paper with the frame-differences and normalization technique
   explained in details::

    @inproceedings{Anjos_IJCB_2011,
      author = {Anjos, Andr{\'{e}} and Marcel, S{\'{e}}bastien},
      keywords = {Attack, Counter-Measures, Counter-Spoofing, Disguise, Dishonest Acts, Face Recognition, Face Verification, Forgery, Liveness Detection, Replay, Spoofing, Trick},
      month = oct,
      title = {Counter-Measures to Photo Attacks in Face Recognition: a public database and a baseline},
      journal = {International Joint Conference on Biometrics 2011},
      year = {2011},
      pdf = {http://publications.idiap.ch/downloads/papers/2011/Anjos_IJCB_2011.pdf}
    }

2. Bob as the core framework used to run the experiments::

    @inproceedings{Anjos_ACMMM_2012,
        author = {A. Anjos AND L. El Shafey AND R. Wallace AND M. G\"unther AND C. McCool AND S. Marcel},
        title = {Bob: a free signal processing and machine learning toolbox for researchers},
        year = {2012},
        month = oct,
        booktitle = {20th ACM Conference on Multimedia Systems (ACMMM), Nara, Japan},
        publisher = {ACM Press},
    }

If you wish to report problems or improvements concerning this code, please
contact the authors of the above mentioned papers.

Raw data
--------

This method was originally conceived to work with the `the PRINT-ATTACK
database <https://www.idiap.ch/dataset/printattack>`_, but has since evolved to
work with the whole of the `the REPLAY-ATTACK database
<https://www.idiap.ch/dataset/replayattack>`_, which is a super-set of the
PRINT-ATTACK database. You are allowed to select protocols in each of the
applications described in this manual.

The data used in these experiments is publicly available and should be
downloaded and installed **prior** to try using the programs described in this
package.

Annotations
-----------

Annotations for this work were generated with the free-software package called
`flandmark <http://cmp.felk.cvut.cz/~uricamic/flandmark/>`. Please cite that
work as well if you use the results of this package on your own publication.

Installation
------------

.. note:: 

  If you are reading this page through our GitHub portal and not through PyPI,
  note **the development tip of the package may not be stable** or become
  unstable in a matter of moments.

  Go to `http://pypi.python.org/pypi/antispoofing.eyeblink
  <http://pypi.python.org/pypi/antispoofing.eyeblink>`_ to download the latest
  stable version of this package.

There are 2 options you can follow to get this package installed and
operational on your computer: you can use automatic installers like `pip
<http://pypi.python.org/pypi/pip/>`_ (or `easy_install
<http://pypi.python.org/pypi/setuptools>`_) or manually download, unpack and
use `zc.buildout <http://pypi.python.org/pypi/zc.buildout>`_ to create a
virtual work environment just for this package.

Using an automatic installer
============================

Using ``pip`` is the easiest (shell commands are marked with a ``$`` signal)::

  $ pip install antispoofing.eyeblink

You can also do the same with ``easy_install``::

  $ easy_install antispoofing.eyeblink

This will download and install this package plus any other required
dependencies. It will also verify if the version of Bob you have installed
is compatible.

This scheme works well with virtual environments by `virtualenv
<http://pypi.python.org/pypi/virtualenv>`_ or if you have root access to your
machine. Otherwise, we recommend you use the next option.

Using ``zc.buildout``
=====================

Download the latest version of this package from `PyPI
<http://pypi.python.org/pypi/antispoofing.eyeblink>`_ and unpack it in your
working area. The installation of the toolkit itself uses `buildout
<http://www.buildout.org/>`_. You don't need to understand its inner workings
to use this package. Here is a recipe to get you started::
  
  $ python bootstrap.py 
  $ ./bin/buildout

These 2 commands should download and install all non-installed dependencies and
get you a fully operational test and development environment.

.. note::

  The python shell used in the first line of the previous command set
  determines the python interpreter that will be used for all scripts developed
  inside this package. Because this package makes use of `Bob
  <http://idiap.github.com/bob>`_, you must make sure that the ``bootstrap.py``
  script is called with the **same** interpreter used to build Bob, or
  unexpected problems might occur.

  If Bob is installed by the administrator of your system, it is safe to
  consider it uses the default python interpreter. In this case, the above 3
  command lines should work as expected. If you have Bob installed somewhere
  else on a private directory, edit the file ``buildout.cfg`` **before**
  running ``./bin/buildout``. Find the section named ``external`` and edit the
  line ``egg-directories`` to point to the ``lib`` directory of the Bob
  installation you want to use. For example::

    [external]
    recipe = xbob.buildout:external
    egg-directories=/Users/crazyfox/work/bob/build/lib

User Guide
----------

It is assumed you have followed the installation instructions for the package
and got this package installed and the REPLAY-ATTACK (or PRINT-ATTACK) database
downloaded and uncompressed in a directory to which you have read access.
Through this manual, we will call this directory ``/root/of/database``. That
would be the directory that *contains* the sub-directories ``train``, ``test``,
``devel`` and ``face-locations``.

Note for Grid Users
===================

At Idiap, we use the powerful Sun Grid Engine (SGE) to parallelize our job
submissions as much as we can. At the Biometrics group, we have developed a
`little toolbox <http://pypi.python.org/pypi/gridtk>` that can submit and
manage jobs at the Idiap computing grid through SGE.  If you are at Idiap, you
can download and install this toolset by adding ``gridtk`` at the ``eggs``
section of your ``buildout.cfg`` file, if it is not already there. If you are
not, you still may look inside for tips on automated parallelization of
scripts.

The following sections will explain how to reproduce the paper results in
single (non-gridified) jobs. A note will be given where relevant explaining how
to parallalize the job submission using ``gridtk``.

.. note::

  If you decide to run using the grid at Idiap, please note that our Lustre
  filesystem does not work well with SQLite. So, do **not** place the
  ``xbob.db.replay`` package inside that filesystem. You can and **should**
  save your results on ``/idiap/temp`` though.

Calculate Frame Differences
===========================

The eye-blink detector calculates normalized frame differences like our face
*versus* background motion detector at the `antispoofing.motion package
<http://pypi.python.org/pypi/antispoofing.motion>`_, except it does it for
the eye region and face remainer (the part of the face that does not contain
the eye region). In the first stage of the processing, we compute the eye
and face remainder regions normalized frame differences for each input video.
To do this, just execute::

  $ ./bin/framediff.py /root/of/database /root/of/annotations results/framediff

There are more options for the `framediff.py` script you can use (such as the
sub-protocol selection). Note that, by default, all applications are tunned to
work with the **whole** of the replay attack database. Just type `--help` at
the command line for instructions.

There is one parameter in special you may need tunning on the above script,
which relates to the ``--maximum-displacement`` option. This option controls
the percentage in eye-center movement in which the method still considers the
current detection is valid, w.r.t. the previous frame. If the eye-center
positions between the current and previous frame move more than the specified
ratio of the eye-width, then the detection is considered invalid and is
discarded.

.. note::

  To parallelize this job, do the following::

    $ ./bin/jman submit --array=1300 ./bin/framediff.py /root/of/database /root/of/annotations results/framediff

  The `magic` number of `1300` entries can be found by executing::

    $ ./bin/framediff.py --grid-count

  Which just prints the number of jobs it requires for the grid execution.

Creating Partial Score Files
============================

To create the final score files, you will need to execute ``make_scores.py``,
which contains a simple strategy for producing a single score per input frame
in every video. The final score is calculated from the input eye and face
remainder frame differences in the following way::

  S = ratio(eye/face_rem) - running_average(ratio(eye/face_rem))

  The final score is set to S, unless any of the following conditions are met:

  1
    S < running_std_deviation(ratio(...))

  2
    eye == 0

  3
    S < running_average(ratio(...))

  In these cases S is replaced by the output of running_average(ratio(...)).

To compute the scores ``S`` for every frame in every input video, do the
following::

  $ ./bin/make_scores.py --verbose results/framediff results/partial_scores

There are more options for the `framediff.py` script you can use (such as the
sub-protocol selection). Note that, by default, all applications are tunned to
work with the **whole** of the replay attack database. Just type `--help` at
the command line for instructions.

We don't provide a grid-ified version of this step because the job runs quite
fast, even for the whole database.

Counting Eye-Blinks
===================

The next step of the process is to use the partial scores for each video (a
signal through time) to count the number of blinks perceived in every database
element. You can use the ``count_blinks.py`` script for that::

  $ ./bin/count_blinks.py --verbose results/partial_scores results/blinks

The output files will have integer values as scores for each frame, with the
number of blinks accounted up to that point in time. These files can be used as
score output files for fusion processes.

Merging Scores
==============

If you wish to create a single `5-column format file
<http://www.idiap.ch/software/bob/docs/nightlies/last/bob/sphinx/html/measure/index.html?highlight=five_col#bob.measure.load.five_column>`_
by combining this counter-measure scores for every video into a single file
that can be fed to external analysis utilities such as our
`antispoofing.evaluation <http://pypi.python.org/pypi/antispoofing.evaluation>`
package, you should use the script ``count_blinks.py``. The merged scores
represent the number of eye-blinks computed for each video sequence. You will
have to specify how many of the scores in every video you will want to consider
and the input directory containing the scores files that will be merged (by
default, the procedure considers only the first 220 frames, which is some sort
of *common denominator* between real-access and attack video number of frames).

The output of the program consists of a single 5-column formatted file with the
client identities and scores for **every video** in the input directory. A line
in the output file corresponds to a video from the database. 

You run this program on the output of ``make_scores.py``. So, it should look
like this if you followed the previous example::

  $ ./bin/merge_scores.py --verbose results/partial_scores results/blinks

The above commandline example will generate 3 text files on the ``results``
directory containing the training, development and test scores, accumulated
over each video in the respective subsets. You can use other options to limit
the number of outputs in each file such as the protocol or support to use.

There are two main options you may need to tweak on this program:
``--skip-frames`` and ``--threshold-ratio``. The first one, ``--skip-frames``,
determines how many frames to skip between eye-blinks, to avoid multiple
eye-blink detections on a single user blink (defaults to ``10``). The other
parameter defines how many standard-deviations from the running mean, a given
signal peak should be considered as originating from an eye-blink. It is set by
default to ``3.0``.

Creating Movies
===============

You can create animated movies showing the detector operation using the
``make_movie.py`` script. This script will combine all the above steps in the
detection process and will generate a movie file showing the original input
movie that is being analyzed, facial landmarks, the light normalization result
and the resulting score evolution, together with instantaneous eye-blink
thresholds. You can use it to debug the eye-blinking detector and better tune
the parameters for batch processing. The script takes the full path to a movie
file in the REPLAY-ATTACK database and an output movie filename::

  $ ./bin/make_movie.py database/train/attack/hand/attack_print_client001_session01_highdef_photo_controlled.mov test.avi

You can use many of the tweaking options defined in the batch processing
scripts to fine tune the output behavior. Use ``--help`` to find-out more
information about this program.

Problems
--------

In case of problems, please contact any of the authors of the paper.
