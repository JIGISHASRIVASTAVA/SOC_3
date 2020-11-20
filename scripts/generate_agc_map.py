"""
  GEF5-SLM: Above ground carbon estimation in thicket using multi-spectral images
  Copyright (C) 2020 Dugal Harris
  Released under GNU Affero General Public License (AGPL) (https://www.gnu.org/licenses/agpl.html)
  Email: dugalh@gmail.com
"""

from agc_estimation import imaging as img
import pathlib, sys, os
import logging
import joblib

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if '__file__' in globals():
    root_path = pathlib.Path(__file__).absolute().parents[1]
else:
    root_path = pathlib.Path(os.getcwd())

sys.path.append(str(root_path.joinpath('Code')))
logging.basicConfig(format='%(levelname)s %(name)s: %(message)s')

image_filename = r"D:/OneDrive/GEF Essentials\Source Images\WorldView3 Oct 2017\WorldView3_Oct2017_OrthoNgiDem_AtcorSrtmAdjCorr_PanAndPandSharpMs.tif"

if True:
    map_filename = root_path.joinpath(r'data\outputs\geospatial\gef5_slm_wv3_oct_2017_univariate_agc_10m.tif')
    model_filename = root_path.joinpath(r'data\outputs\Models\best_univariate_model_py38_cv5v2.joblib')
else:
    map_filename = root_path.joinpath(r'data\outputs\geospatial\gef5_slm_wv3_oct_2017_multivariate_agc_10m.tif')
    model_filename = root_path.joinpath(r'data\outputs\Models\best_multivariate_model_py38_cv5v2.joblib')

# gdal command lines (gdal v3+ to work with qgis)
# build pan and pansharp vrt with nodata
# gdalbuildvrt -separate -srcnodata 0 -vrtnodata 0 test.vrt ATCORCorrected_o17OCT01084657-P2AS_R1C12-058217622010_01_P001_PhotoscanDEM_14128022.pix ATCORCorrected_o17OCT01084657-P2AS_R1C12-058217622010_01_P001_PhotoscanDEM_14128022_PanSharp.pix
# convert vrt to tiff (pcidisk driver has a bug)
# gdal_translate -of GTiff -co "TILED=YES" -co "COMPRESS=DEFLATE" -co "BIGTIFF=YES" -co NUM_THREADS=ALL_CPUS -a_nodata 0 o17OCT01084657-M2AS_R1C12-058217622010_01_P001_PanAndPansharpMS_gdalv3.vrt o17OCT01084657-M2AS_R1C12-058217622010_01_P001_PanAndPansharpMS.tif
# gdaladdo -ro -r average --config COMPRESS_OVERVIEW DEFLATE --config PHOTOMETRIC_OVERVIEW RGB --config INTERLEAVE_OVERVIEW BAND o17OCT01084657-M2AS_R1C12-058217622010_01_P001_PanAndPansharpMS.tif 2 4 8 16 32 64 128

model, model_keys, model_scores = joblib.load(model_filename)

# model, model_keys = pickle.load(open(model_filename, 'rb'), encoding='latin1')
#
# if sys.version_info.major == 3 and (type(model_keys[0]) is bytes or type(model_keys[0]) is np.bytes_):
#     model_keys = [sk.decode() for sk in model_keys]       # convert bytes to unicode for py 3
# print([(i,key) for i,key in enumerate(model_keys)])

mapper = img.ApplyLinearModel(in_file_name=image_filename, out_file_name=map_filename, model=model, model_keys=model_keys,
                             save_feats=False)

mapper.create(win_size=(33, 33), step_size=(33, 33))
mapper.post_proc()

# gdal_fillnodata -md 20 -si 0 -b 1 o17OCT01084657-M2AS_R1C12-058217622010_01_P001_AGC_Py27Cv5v2_24Feat_10m.tif -of GTiff -co COMPRESS=DEFLATE o17OCT01084657-M2AS_R1C12-058217622010_01_P001_AGC_Py27Cv5v2_24Feat_10m_fillnodata.tif
# gdal_merge -o GEF_WV3_Oct2017_AGC_10m.tif -co COMPRESS=DEFLATE -separate -a_nodata nan o17OCT01084657-M2AS_R1C12-058217622010_01_P001_AGC_Py27Cv5v2_1Feat_10m_postproc.tif o17OCT01084657-M2AS_R1C12-058217622010_01_P001_AGC_Py27Cv5v2_24Feat_10m_postproc.tif

# tmp = np.ones((3,3))
# tmp2 = np.hstack((tmp,tmp*2,tmp*3,tmp*4,tmp*5))
# pfe = img.PatchFeatureExtractor(num_bands=9, rolling_window_xsize=3, rolling_window_xstep=3)
# pfe.__rolling_window_view(tmp2)
