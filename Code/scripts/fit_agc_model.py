# use SpatialUtils to produce models and plots for report

import rasterio
import numpy as np
import geopandas as gpd, pandas as pd
import pathlib, sys, os, glob, warnings
from sklearn import linear_model
from modules import SpatialUtils as su
from matplotlib import pyplot
import logging

if '__file__' in globals():
    root_path = pathlib.Path(__file__).absolute().parents[2]
else:
    root_path = pathlib.Path(os.getcwd()).parents[0]

sys.path.append(str(root_path.joinpath('Code')))
logging.basicConfig(format='%(levelname)s %(name)s: %(message)s')

from sklearn import metrics

# reload(su)

def scatter_y_pred(y, pred, scores):
    import matplotlib.pyplot as plt
    su.scatter_plot(y, pred, xlabel='Measured AGC (t C ha$^{-1}$)', ylabel='Predicted AGC (t C ha$^{-1}$)', do_regress = False)
    # fig, ax = pyplot.subplots()
    # pyplot.plot(y, pred, 'o')
    mn = np.min([y, pred])
    mx = np.max([y, pred])
    h, = plt.plot([0, mx], [0, mx], 'k--', lw=2, zorder=-1, label='1:1')
    # ax.set_xlabel('Measured AGC (tC/ha)')
    # ax.set_ylabel('Estimated AGC (tC/ha)')
    pyplot.xlim(0, mx)
    pyplot.ylim(0, mx)
    # pyplot.grid()
    pyplot.text(26, 5, str.format('$R^2$ = {0:.2f}', scores['R2_stacked']),
               fontdict={'size': 11})
    pyplot.text(26, 2, str.format('RMSE = {0:.2f} t C ha{1}',np.abs(scores['test_user']).mean(),'$^{-1}$'),
               fontdict={'size': 11})
    pyplot.show()
    pyplot.tight_layout()
    pyplot.legend([h], ['1:1'], frameon=False)

#--------------------------------------------------------------------------------------------------------------
# WV3 im analysis
plot_agc_shapefile_name = root_path.joinpath(r'Data\Outputs\Geospatial\GEF Plot Polygons with AGC v2.shp')
image_filename = r"D:\OneDrive\GEF Essentials\Source Images\WorldView3 Oct 2017\WorldView3_Oct2017_OrthoNgiDem_AtcorSrtmAdjCorr_PanAndPandSharpMs.tif"

plot_agc_gdf = gpd.GeoDataFrame.from_file(plot_agc_shapefile_name)


# vr = su.GdalVectorReader(plot_agc_shapefile_name)
# ld = vr.read()
# imr = su.GdalImageReader(imageFile)
with rasterio.open(image_filename, 'r') as imr:
    fex = su.ImPlotFeatureExtractor(image_reader=imr, plot_data_gdf=plot_agc_gdf)
    im_plot_data_gdf = fex.extract_all_features(patch_fn=su.ImPlotFeatureExtractor.extract_patch_ms_features_ex)
    # im_plot_data_gdf.pop('ST49')

# fix stratum labels
im_plot_data_gdf.loc[im_plot_data_gdf['data']['Stratum'] == 'Degraded', ('data', 'Stratum')] = 'Severe'
im_plot_data_gdf.loc[im_plot_data_gdf['data']['Stratum'] == 'Intact', ('data', 'Stratum')] = 'Pristine'

# X = im_plot_data_gdf['feats'].to_numpy()

# implot_feat_dict.pop('ST49')
X, y, feat_keys = fex.get_feat_array_ex(y_data_key='AgcHa')

pyplot.figure()
# su.scatter_ds(im_plot_data_gdf, x_col=('feats','pan/R'), y_col=('data','AgcHa'), class_col=('data','Stratum'),
#               xfn=lambda x: np.log10(x), do_regress=True)
su.scatter_ds(im_plot_data_gdf, x_col=('feats','pan/R'), y_col=('data','AgcHa'), class_col=('data','Stratum'),
              xfn=lambda x: np.log10(x), do_regress=True, thumbnail_col=('data','thumbnail'), label_col=('data', 'ID'))
# fex.scatter_plot(x_feat_key='pan/R', y_feat_key='AgcHa', class_key='Stratum', xfn=lambda x: np.log10(x), do_regress=True)


# R^2 = 0.8306
# P (slope=0) = 0.000000
# Slope = -404187.9402
# Std error of slope = 19458.2934
# RMS error = 7976.5274
# Out[8]: (0.83059870877446296, 7976.5274329637823)
pyplot.figure()
fex.scatter_plot(x_feat_key='pan/R', y_feat_key='AbcHa', class_key='DegrClass', xfn=lambda x: np.log10(x), do_regress=True)

pyplot.figure()
fex.scatter_plot(x_feat_key='(R/G)^2', y_feat_key='AgcHa', class_key='DegrClass', xfn=lambda x: np.log10(x), do_regress=True)

# pyplot.figure()
# fex.scatter_plot(x_feat_key='diss(GLCM)[-1]', y_feat_key='AgcHa', class_key='DegrClass', xfn=lambda x: np.log10(x), do_regress=True)


# R^2 = 0.7969
# P (slope=0) = 0.000000
# Slope = -345057.5197
# Std error of slope = 18568.0446
# RMS error = 7611.5882
# Out[9]: (0.79692760413684294, 7611.5882494785465)

# forward selection of features use RMSE criterion (R2 is potentially suspect in CV scenario)
# reload(su)
Xselected_feats, selected_scores, selected_keys = su.FeatureSelector.forward_selection(X, y, feat_keys=feat_keys, max_num_feats=41, cv=5,  #cv=X.shape[0] / 5
                                                                                       score_fn=lambda y,pred: -np.sqrt(metrics.mean_squared_error(y, pred)))


#------------------------------------------------------------------------------------------------------------------------
# make plots of num feats vs r2 / RMSE
r2 = np.zeros(selected_scores.__len__())
rmse = np.zeros(selected_scores.__len__())
rmse_ci = np.zeros((selected_scores.__len__(),2))
num_feats = np.arange(1, len(selected_scores)+1)
for i in range(0, selected_scores.__len__()):
    scores, predicted = su.FeatureSelector.score_model(Xselected_feats[:, :i+1], y, model=linear_model.LinearRegression(), find_predicted=True, cv=X.shape[0])
    r2[i] = scores['R2_stacked']
    rmse_v = np.abs(scores['test_user'])/1000.
    rmse[i] = rmse_v.mean()
    rmse_ci[i,:] = np.percentile(rmse_v, [5, 95])
    print('.', end=' ')
print(' ')

# fontSize = 12.
# pyplot.rcParams.update({'font.size': fontSize})

# plots for report
fig = pyplot.figure()
fig.set_size_inches(8, 6, forward=True)
pyplot.subplot(2, 1, 1)
pyplot.plot(num_feats, r2, 'k-')
pyplot.xlabel('Number of features')
pyplot.ylabel('$\mathit{R}^2$')
# pyplot.grid()
pyplot.tight_layout()
pyplot.subplot(2, 1, 2)
pyplot.plot(num_feats, rmse, 'k-')
pyplot.xlabel('Number of features')
pyplot.ylabel('RMSE (t C ha$^{-1}$)')
# pyplot.grid()
pyplot.tight_layout()
fig.savefig(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\AgcAccVsNumFeatsPy38Cv5.png', dpi=300)

fig, ax1 = pyplot.subplots()
fig.set_size_inches(8, 4, forward=True)
color = 'tab:red'
ax1.set_xlabel('Number of features')
ax1.set_ylabel('$\mathit{R}^2$', color=color)  # we already handled the x-label with ax1
ax1.plot(num_feats, r2, color=color)
ax1.tick_params(axis='y', labelcolor=color)
# pyplot.grid()
ax2 = ax1.twinx()
color = 'tab:blue'
ax2.set_ylabel('-RMSE (t C ha$^{-1}$)', color=color)  # we already handled the x-label with ax1
ax2.plot(num_feats, -rmse, color=color)
ax2.tick_params(axis='y', labelcolor=color)
# pyplot.grid()
fig.tight_layout()  # otherwise the right y-label is slightly clipped
pyplot.show()
fig.savefig(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\AgcAccVsNumFeatsPy38Cv5.png', dpi=300)

#------------------------------------------------------------------------------------------------------------------------
# report scatter plots for best and single feature models
print('\nBest model scores:')
best_model_idx = np.argmin(rmse)
scores, predicted = su.FeatureSelector.score_model(Xselected_feats[:, :best_model_idx+1], old_div(y,1000), model=linear_model.LinearRegression(),
                                                   find_predicted=True, cv=X.shape[0], print_scores=True)

print('\nBest model features:')
for k in selected_keys[:best_model_idx+1]:
    print(k)

lm = linear_model.LinearRegression()
lm.fit(Xselected_feats[:, :best_model_idx+1], old_div(y,1000))
for c in lm.coef_:
    print('{0:.4f}'.format(c))

if False:   # write out models to files
    import joblib
    import pickle
    lm = linear_model.LinearRegression()
    lm.fit(Xselected_feats[:, :best_model_idx + 1], old_div(y, 1000))
    joblib.dump([lm, selected_keys[:best_model_idx + 1]], r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\bestModelPy38Cv5v1.joblib')
    pickle.dump([lm, selected_keys[:best_model_idx + 1]], open(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\bestModelPy38Cv5v1.pickle', 'wb'))

    lm = linear_model.LinearRegression()
    lm.fit(Xselected_feats[:, :1], old_div(y, 1000))
    joblib.dump([lm, selected_keys[:1]], r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\bestSingleTermModelPy38Cv5v1.joblib')
    pickle.dump([lm, selected_keys[:1]], open(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\bestSingleTermModelPy38Cv5v1.pickle', 'wb'))

    # print

if False:
    from sklearn.kernel_ridge import KernelRidge
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVR
    from sklearn import pipeline

    pl = pipeline.make_pipeline(StandardScaler(), SVR(kernel='rbf', C=100, gamma=1.))
    scores, predicted = su.FeatureSelector.score_model(Xselected_feats, old_div(y,1000), model=pl,
                                                       find_predicted=True, cv=X.shape[0], print_scores=True)

    scores, predicted = su.FeatureSelector.score_model(Xselected_feats[:, :best_model_idx+1], old_div(y,1000), model=KernelRidge(kernel='rbf', alpha=.1), find_predicted=True, cv=X.shape[0], print_scores=True)

    scores, predicted = su.FeatureSelector.score_model(Xs, y, model=SVR(kernel='linear', C=200), cv=10)

    scores, predicted = su.FeatureSelector.score_model(Xselected_feats_s, y, model=SVR(kernel='linear', C=1000000, gamma='auto'), cv=10)


# su.scatter_plot(y/1000., predicted/1000., labels=implot_feat_dict.keys())
fig = pyplot.figure()
fig.set_size_inches(5, 4, forward=True)
scatter_y_pred(y/1000., predicted, scores)
fig.savefig(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\MeasVsPredAgcBestModel.png', dpi=300)

if False:
    fig = pyplot.figure()
    su.scatter_plot(y/1000., predicted, labels=list(implot_feat_dict.keys()))

fig = pyplot.figure()
fig.set_size_inches(10, 4, forward=True)
pyplot.subplot(1,2,1)
scatter_y_pred(y/1000., predicted, scores)
pyplot.title('(a)')
pyplot.subplot(1,2,2)
print('\nBest single feature model scores:')
scores, predicted = su.FeatureSelector.score_model(Xselected_feats[:, :1], y/1000., model=linear_model.LinearRegression(),
                                                   find_predicted=True, cv=X.shape[0], print_scores=True)
scatter_y_pred(y/1000., predicted, scores)
pyplot.title('(b)')
fig.savefig(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\MeasVsPredAgcBestModels.png', dpi=300)

#------------------------------------------------------------------------------------------------------------------------
# Correlation analysis of the ground cover classification
import modules.SpatialUtils as su
import pyplot
import numpy as np
from sklearn import linear_model, metrics
reload(su)

plot_agc_shapefile_name = "C:/Data/Development/Projects/PhD GeoInformatics/Data/GEF Sampling/GEF Plot Polygons with Agc v5.shp"
# imageFile = r"D:/Data/Development/Projects/PhD GeoInformatics/Data/Digital Globe/058217622010_01/PCI Output/ATCOR/SRTM+AdjCorr Aligned Photoscan DEM/ATCORCorrected_o17OCT01084657-P2AS_R1C12-058217622010_01_P001_PhotoscanDEM_14128022_PanSharp.pix"
clf_file = r"D:\Data\Development\Projects\PhD GeoInformatics\Data\NGI\GEF DEM\DSM Working\ground_clf2.tif"

vr = su.GdalVectorReader(plot_agc_shapefile_name)
ld = vr.read()
imr_clf = su.GdalImageReader(clf_file)
fex_clf = su.ImPlotFeatureExtractor(image_reader=imr_clf, plot_feat_dict=ld['GEF Plot Polygons with Agc v5'])
implot_feat_dict_clf = fex_clf.extract_all_features(patch_fn=su.ImPlotFeatureExtractor.extract_patch_clf_features)

# set DegrClass field in implot_feat_dict using plot ID
for f in list(implot_feat_dict_clf.values()):
    id = f['ID']
    if id[0] == 'S' or id[:3] == 'TCH':
        f['DegrClass'] = 'Severe'
    elif id[0] == 'M':
        f['DegrClass'] = 'Moderate'
    elif id[0] == 'P' or id[:3] == 'INT':
        f['DegrClass'] = 'Pristine'
    else:
        f['DegrClass'] = '?'

X_clf, y_clf, feat_keys_clf = fex_clf.get_feat_array_ex(y_data_key='AgcHa')
feat_scores = su.FeatureSelector.ranking(X_clf, y_clf, feat_keys=feat_keys_clf)
classes = [plot['DegrClass'] for plot in list(implot_feat_dict_clf.values())]

pyplot.figure()
fex_clf.scatter_plot(x_feat_key='VegCover', y_feat_key='AgcHa', do_regress=True, class_key='DegrClass', show_labels=False, yfn= lambda x: x/1000.)
pyplot.xlabel('Veg. cover (%)')
pyplot.ylabel('AGC (tC/ha)')
pyplot.tight_layout()

# feature selection and model plot
Xselected_feats, selected_scores, selected_keys = su.FeatureSelector.forward_selection(X_clf, y_clf, feat_keys=feat_keys_clf, max_num_feats=4, cv=5,
    score_fn = lambda y, pred: -np.sqrt(metrics.mean_squared_error(y, pred)))
scores, predicted = su.FeatureSelector.score_model(Xselected_feats[:, :np.argmax(selected_scores)+1], y_clf, model=linear_model.LinearRegression(),
                                                   find_predicted=True, cv=X_clf.shape[0], print_scores=True)

scatter_y_pred(y_clf/1000., predicted/1000., scores)



# ----------------------------------------------------------------------------------------------------------------------
# NGI image analysis
plot_agc_shapefile_name = "C:/Data/Development/Projects/PhD GeoInformatics/Data/GEF Sampling/GEF Plot Polygons with Agc v5.shp"
# imageFile = r"V:/Data/NGI/Rectified/3323D_2015_1001/RGBN/XCALIB/o3323d_2015_1001_GEF_RGBN_XCALIB.vrt"  # ""V:/Data/NGI/Rectified/3323D_2015_1001/RGBN/o3323d_2015_1001_02_0077_Lo25Wgs84_RGBN_XCALIB.tif"
image_filename = r"D:\Data\Development\Projects\PhD GeoInformatics\Data\NGI\Rectified\3322D_2015_1001\RGBN\XCALIB\AutoGcpWv3\o3323D_2015_1001_GEF_RGBN_XCALIb_v2.vrt"
# imageFile = r"D:\Data\Development\Projects\PhD GeoInformatics\Data\NGI\Rectified\3322D_2015_1001\RGBN\AutoGcpWv3\3323d_2015_OrthoRect.vrt"

reload(su)

vr = su.GdalVectorReader(plot_agc_shapefile_name)
ld = vr.read()
imr = su.GdalImageReader(image_filename)
fex = su.ImPlotFeatureExtractor(image_reader=imr, plot_feat_dict=ld['GEF Plot Polygons with Agc v5'])
implot_feat_dict = fex.extract_all_features(patch_fn=su.ImPlotFeatureExtractor.extract_patch_ms_features_ex)

# set DegrClass field in implot_feat_dict using plot ID
for f in list(implot_feat_dict.values()):
    id = f['ID']
    if id[0] == 'S' or id[:3] == 'TCH':
        f['DegrClass'] = 'Severe'
    elif id[0] == 'M':
        f['DegrClass'] = 'Moderate'
    elif id[0] == 'P' or id[:3] == 'INT':
        f['DegrClass'] = 'Pristine'
    else:
        f['DegrClass'] = '?'

pyplot.figure()
fex.scatter_plot(x_feat_key='R/pan', y_feat_key='AgcHa', class_key='DegrClass', xfn=lambda x: np.log10(x))
pyplot.xlabel('R/pan')
pyplot.ylabel('AGC (tC/ha)')
pyplot.tight_layout()

pyplot.figure()
fex.scatter_plot(x_feat_key='NDVI', y_feat_key='AgcHa', class_key='DegrClass', xfn=lambda x: np.log10(x+1.))
pyplot.xlabel('NDVI')
pyplot.ylabel('AGC (tC/ha)')
pyplot.tight_layout()

vr.cleanup()
imr.cleanup()

X, y, feat_keys = fex.get_feat_array_ex(y_data_key='AgcHa')
Xselected_feats, selected_scores, selected_keys = su.FeatureSelector.forward_selection(X, y, feat_keys=feat_keys, max_num_feats=30, cv=5,
                                                                                       score_fn=lambda y,pred: -np.sqrt(metrics.mean_squared_error(y, pred)))

#------------------------------------------------------------------------------------------------------------------------
# make plots of num feats vs r2 / RMSE
r2 = np.zeros(selected_scores.__len__())
rmse = np.zeros(selected_scores.__len__())
rmse_ci = np.zeros((selected_scores.__len__(),2))
num_feats = np.arange(1, len(selected_scores)+1)
for i in range(0, selected_scores.__len__()):
    scores, predicted = su.FeatureSelector.score_model(Xselected_feats[:, :i+1], y, model=linear_model.LinearRegression(), find_predicted=True, cv=X.shape[0])
    r2[i] = scores['R2_stacked']
    rmse_v = np.abs(scores['test_user'])/1000.
    rmse[i] = rmse_v.mean()
    rmse_ci[i,:] = np.percentile(rmse_v, [5, 95])
    print('.', end=' ')
print(' ')

# fontSize = 12.
# pyplot.rcParams.update({'font.size': fontSize})

# plots for report
fig = pyplot.figure()
fig.set_size_inches(8, 6, forward=True)
pyplot.subplot(2,1,1)
pyplot.plot(num_feats, r2, 'k-')
pyplot.xlabel('Number of features')
pyplot.ylabel('$\mathit{R}^2$')
# pyplot.grid()
pyplot.tight_layout()
pyplot.subplot(2,1,2)
pyplot.plot(num_feats, rmse, 'k-')
pyplot.xlabel('Number of features')
pyplot.ylabel('RMSE (t C ha$^{-1}$)')
# pyplot.grid()
pyplot.tight_layout()
fig.savefig(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\NgiAgcAccVsNumFeats1.png', dpi=300)

fig, ax1 = pyplot.subplots()
fig.set_size_inches(8, 4, forward=True)
color = 'tab:red'
ax1.set_xlabel('Number of features')
ax1.set_ylabel('$\mathit{R}^2$', color=color)  # we already handled the x-label with ax1
ax1.plot(num_feats, r2, color=color)
ax1.tick_params(axis='y', labelcolor=color)
# pyplot.grid()
ax2 = ax1.twinx()
color = 'tab:blue'
ax2.set_ylabel('-RMSE (t C ha$^{-1}$)', color=color)  # we already handled the x-label with ax1
ax2.plot(num_feats, -rmse, color=color)
ax2.tick_params(axis='y', labelcolor=color)
# pyplot.grid()
fig.tight_layout()  # otherwise the right y-label is slightly clipped
pyplot.show()
fig.savefig(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\NgiAgcAccVsNumFeats2.png', dpi=300)

#------------------------------------------------------------------------------------------------------------------------
# report scatter plots for best and single feature models
print('\nBest model scores:')
best_model_idx = np.argmin(rmse)
scores, predicted = su.FeatureSelector.score_model(Xselected_feats[:, :best_model_idx+1], old_div(y,1000), model=linear_model.LinearRegression(),
                                                   find_predicted=True, cv=X.shape[0], print_scores=True)

print('\nBest model features:')
for k in selected_keys[:best_model_idx+1]:
    print(k)

# su.scatter_plot(y/1000., predicted/1000., labels=implot_feat_dict.keys())
fig = pyplot.figure()
fig.set_size_inches(5, 4, forward=True)
scatter_y_pred(y/1000., predicted, scores)
fig.savefig(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\MeasVsNgiPredAgcBestModel.png', dpi=300)

fig = pyplot.figure()
fig.set_size_inches(10, 4, forward=True)
pyplot.subplot(1, 2, 1)
scatter_y_pred(y/1000., predicted, scores)
pyplot.title('(a)')
pyplot.subplot(1, 2, 2)
print('\nBest single feature model scores:')
scores, predicted = su.FeatureSelector.score_model(Xselected_feats[:, :1], old_div(y,1000), model=linear_model.LinearRegression(),
                                                   find_predicted=True, cv=X.shape[0], print_scores=True)
scatter_y_pred(y/1000., predicted, scores)
pyplot.title('(b)')
fig.savefig(r'C:\Data\Development\Projects\PhD GeoInformatics\Docs\Funding\GEF5\Invoices, Timesheets and Reports\Final Report\MeasVsNgiPredAgcBestModels.png', dpi=300)