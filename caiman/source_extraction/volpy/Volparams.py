import logging

import numpy as np
import scipy
from scipy.ndimage.morphology import generate_binary_structure, iterate_structure

#from ...paths import caiman_datadir
#from .utilities import dict_compare, get_file_size

from pprint import pformat

class volparams(object):

    def __init__(self, fnames=None, fr=None, index=None, ROIs=None, doCrossVal=False, doGlobalSubtract=False,
            contextSize=50, censorSize=12, nPC_bg=8, tau_lp=3, tau_pred=1, sigmas=np.array([1,1.5,2]),
            nIter=5, localAlign=False, globalAlign=False, highPassRegression=False, params_dict={}):
        """Class for setting parameters for voltage imaging. Including parameters for the data, motion correction and
        spike detection. The prefered way to set parameters is by using the set function, where a subclass is determined
        and a dictionary is passed. The whole dictionary can also be initialized at once by passing a dictionary
        params_dict when initializing the CNMFParams object.
        """
        self.data = {
            'fnames': fnames, # name of the movie, only memory map file for spike detection
            'fr': fr, # sample rate of the movie
            'index': index, # a list of cell numbers for processing
            'ROIs': ROIs # a 3-d matrix contains all region of interests
        }

        self.volspike = {
            'doCrossVal': doCrossVal, # cross-validate to optimize regression regularization parameters
            'doGlobalSubtract': doGlobalSubtract,
            'contextSize': contextSize, #number of pixels surrounding the ROI to use as context
            'censorSize': censorSize, # number of pixels surrounding the ROI to censor from the background PCA;
            # roughly the spatial scale of scattered/dendritic neural signals, in pixels.
            'nPC_bg': nPC_bg, # number of principle components used for background subtraction
            'tau_lp': tau_lp, # time window for lowpass filter (seconds); signals slower than this will be ignored
            'tau_pred': tau_pred, # time window in seconds for high pass filtering to make predictor for regression
            'sigmas': sigmas, # spatial smoothing radius imposed on spatial filter;
            'nIter': nIter, # number of iterations alternating between estimating temporal and spatial filters
            'localAlign': localAlign,
            'globalAlign': globalAlign,
            'highPassRegression': highPassRegression # regress on a high-passed version of the data. Slightly improves detection of spikes, but makes subthreshold unreliable
        }

        self.motion = {
            'border_nan': 'copy',  # flag for allowing NaN in the boundaries
            'gSig_filt': None,  # size of kernel for high pass spatial filtering in 1p data
            'max_deviation_rigid': 3,  # maximum deviation between rigid and non-rigid
            'max_shifts': (6, 6),  # maximum shifts per dimension (in pixels)
            'min_mov': None,  # minimum value of movie
            'niter_rig': 1,  # number of iterations rigid motion correction
            'nonneg_movie': True,  # flag for producing a non-negative movie
            'num_frames_split': 80,  # split across time every x frames
            'num_splits_to_process_els': [7, None],
            'num_splits_to_process_rig': None,
            'overlaps': (32, 32),  # overlap between patches in pw-rigid motion correction
            'pw_rigid': False,  # flag for performing pw-rigid motion correction
            'shifts_opencv': True,  # flag for applying shifts using cubic interpolation (otherwise FFT)
            'splits_els': 14,  # number of splits across time for pw-rigid registration
            'splits_rig': 14,  # number of splits across time for rigid registration
            'strides': (96, 96),  # how often to start a new patch in pw-rigid registration
            'upsample_factor_grid': 4,  # motion field upsampling factor during FFT shifts
            'use_cuda': False  # flag for using a GPU
        }

        self.change_params(params_dict)
#%%
    def set(self, group, val_dict, set_if_not_exists=False, verbose=False):
        """ Add key-value pairs to a group. Existing key-value pairs will be overwritten
            if specified in val_dict, but not deleted.

        Args:
            group: The name of the group.
            val_dict: A dictionary with key-value pairs to be set for the group.
            set_if_not_exists: Whether to set a key-value pair in a group if the key does not currently exist in the group.
        """

        if not hasattr(self, group):
            raise KeyError('No group in CNMFParams named {0}'.format(group))

        d = getattr(self, group)
        for k, v in val_dict.items():
            if k not in d and not set_if_not_exists:
                if verbose:
                    logging.warning(
                        "NOT setting value of key {0} in group {1}, because no prior key existed...".format(k, group))
            else:
                if np.any(d[k] != v):
                    logging.warning(
                        "Changing key {0} in group {1} from {2} to {3}".format(k, group, d[k], v))
                d[k] = v

#%%
    def get(self, group, key):
        """ Get a value for a given group and key. Raises an exception if no such group/key combination exists.

        Args:
            group: The name of the group.
            key: The key for the property in the group of interest.

        Returns: The value for the group/key combination.
        """

        if not hasattr(self, group):
            raise KeyError('No group in CNMFParams named {0}'.format(group))

        d = getattr(self, group)
        if key not in d:
            raise KeyError('No key {0} in group {1}'.format(key, group))

        return d[key]

    def get_group(self, group):
        """ Get the dictionary of key-value pairs for a group.

        Args:
            group: The name of the group.
        """

        if not hasattr(self, group):
            raise KeyError('No group in CNMFParams named {0}'.format(group))

        return getattr(self, group)


    def change_params(self, params_dict, verbose=False):
        for gr in list(self.__dict__.keys()):
            self.set(gr, params_dict, verbose=verbose)
        for k, v in params_dict.items():
            flag = True
            for gr in list(self.__dict__.keys()):
                d = getattr(self, gr)
                if k in d:
                    flag = False
            if flag:
                logging.warning('No parameter {0} found!'.format(k))
        return self




