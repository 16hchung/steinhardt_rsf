from copy import deepcopy
from pathlib import Path
import numpy as np
import numpy.random
import numpy.linalg

from ovito.io import import_file, export_file
from ovito.data import NearestNeighborFinder

from ..util import constants as C
from ..features import Featurizer

def distort_perfect(perfect_ovfile,
                    distort_bins=C.DFLT_DISTORT_BINS,
                    save_path=None):
  perfect_ovfile = str(perfect_ovfile)
  # First get first_neigh_d which we'll use to determine displacement sampling
  pipeline = import_file(perfect_ovfile)
  perf_data = pipeline.compute()
  n_atoms = perf_data.particles.count

  finder = NearestNeighborFinder(1, perf_data)
  first_neigh_d = min([next(finder.find(i)).distance for i in range(n_atoms)])

  # Include each bin as a separate "frame" in ovito pipeline (typically
  # used to handle time evolution)
  dup_pipeline = import_file([perfect_ovfile] * len(distort_bins))
  def pipeline_add_offsets(i_frame, data):
    distort_scale = distort_bins[i_frame]

    positions = data.particles_.positions
    n_total_points = positions[:].shape[0]
    # generate unit vectors in random directions
    displacements = np.random.randn(3, n_total_points).T
    norms = np.linalg.norm(displacements, axis=1, keepdims=True)
    # generate uni distributed random displacement magnitudes to apply
    mags_cubed = np.random.uniform(0,
                                   (first_neigh_d * distort_scale) ** 3,
                                   size=n_total_points) \
                    .reshape(norms.shape)
    displacements = displacements / norms * np.cbrt(mags_cubed)
    data.particles_.positions_ += displacements

  dup_pipeline.modifiers.append(pipeline_add_offsets)
  ov_collections = [
    dup_pipeline.compute(i) for i in range(dup_pipeline.source.num_frames)
  ]
  if save_path:
    for i, ov_collection in enumerate(ov_collections):
      save_fname = f'distorted_{distort_bins[i]}.dump'
      full_save_path = save_path / save_fname
      export_file(ov_collection,
                  str(full_save_path),
                  C.OV_OUTPUT_FMT,
                  columns=C.OV_CART_COLS)
  return ov_collections

def make_synthetic_liq(perfect_ovfile, save_path=None):
  pipeline = import_file(str(perfect_ovfile))
  data = pipeline.compute()
  n_atoms = data.particles.count
  dims = data.cell[:,:]
  coord_maxes = [dims[i,i] for i in range(3)]

  def pipeline_randomize(i_frame, data):
    cols = [np.random.uniform(0.0, coord_max, n_atoms)[:, np.newaxis]
            for coord_max in coord_maxes]
    data.particles_.positions_[:,:] = np.hstack(cols)

  pipeline.modifiers.append(pipeline_randomize)
  ov_collection = pipeline.compute()
  if save_path:
    full_save_path = save_path / 'synth_liq.dump'
    export_file(ov_collection, 
                str(full_save_path),
                C.OV_OUTPUT_FMT,
                columns=C.OV_CART_COLS)
  return ov_collection
