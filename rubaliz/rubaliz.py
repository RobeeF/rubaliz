# -*- coding: utf-8 -*-
"""
Created on Tue Apr  5 18:52:28 2022

@author: rfuchs
"""

import re
import os
import pandas as pd
import numpy as np
import ruptures as rpt
import matplotlib.pyplot as plt

from .seabird import fCNV

class rubaliz:
    def __init__(self, info_dict):
        '''
        Initialise the rubaliz object

        Parameters
        ----------
        info_dict : dict
            The dictionnary containing the CTD information (cruise, data folder etc).

        Returns
        -------
        None.

        '''
        #====================================
        # Deal with missing info
        #====================================

        legal_fields = ['cruise_name', 'station_name', 'fluo_col', 'pres_col',\
                            'ub_range', 'lb_range', 'oxygen_col', 'temp_col',\
                            'density_col', 'salinity_col', 'files_format', 'sep',\
                            'header', 'data_folder']

        for key in legal_fields:
            if not(key in info_dict.keys()):
                info_dict[key] = None

        # Fill some metadata with the default values
        if info_dict['ub_range'] == None:
            info_dict['ub_range'] = [280, 320]
        if info_dict['lb_range'] == None:
            info_dict['lb_range'] = [1000, 1300]
        if info_dict['sep'] == None:
            info_dict['sep'] = ','

        #====================================
        # Initialise the attributes
        #====================================

        colnames = ['Fluorescence', 'Oxygen', 'Pot. temp.', 'Salinity', 'Density']
        colors = np.array(['green', 'red', 'blue', 'orange', 'black'])

        self.ub_range = info_dict['ub_range'] # upper bound range
        self.lb_range = info_dict['lb_range'] # lower bound range
        self.cruise = info_dict['cruise_name']
        self.station = info_dict['station_name']

        self.pres_col = info_dict['pres_col']

        self.cols = {}
        for col in colnames:
            self.cols[col] = info_dict[col]

        # Keep only the columns existing in the files
        self.available_cols = [colname for col_alias, colname in self.cols.items()\
                               if colname != None]
    
        self.available_aliases = [col_alias for col_alias, colname in self.cols.items()\
                               if colname != None]
        self.available_mask = [True if colname != None else False \
                               for col_alias, colname in self.cols.items()]
        self.available_colors = colors[self.available_mask]

        self.sep = info_dict['sep']
        self.files_format = info_dict['files_format']
        self.data_folder = info_dict['data_folder']
        self.is_fitted = False


    def format_data(self, depth_boundaries, stacked_signals = True, max_depth = None):
        '''
        Fetch the data used in the rupture detection process and
        put all the signals to the same length

        Parameters
        ----------
        depth_boundaries : list or numpy array
            The minimum and maximum depth at which to extract the data.

        info_dict : dict
            The information about the cruise name, the columns to extract etc.

        stacked_signals: Bool
            Whether to put all the signal at the same length

        max_depth: int
            Keep CTDs that reached depths at least equal to max_depth

        Returns
        -------
        pandas DataFrame
            The formatted data with shape:
                (signal depth, number of columns x number of valid CTDs).
        '''

        max_depth = depth_boundaries[1] if max_depth == None else max_depth

        #======================================
        # Fetch the information
        #======================================

        folder = self.data_folder
        seq_start = depth_boundaries[0]
        seq_end = depth_boundaries[1]

        #===========================================
        # Import the files and compute the rupture
        #===========================================

        files = os.listdir(folder)
        files = [file for file in files if re.search(self.files_format, file)]

        if len(files) == 0:
            raise RuntimeError('No files in the folder ' + folder)

        flc_signals = []

        for fname in files:

            #*******************
            # Format handling
            #*******************

            path = os.path.join(folder, fname)

            if self.files_format in ['.txt', '.csv']:
                down = pd.read_csv(path, sep  = self.sep, engine = 'python', header = 0)
            elif self.files_format == '.cnv':
                down = fCNV(path).as_DataFrame()
            else:
                raise ValueError('Please enter a valid file_format: .txt, .csv, .cnv')

            if down.shape[1] < 2:
                raise ValueError('There is only one column in the corresponding file,\
                                 please check the file ' + fname + ' or the separator\
                                 provided in info_dict')

            #**************************************
            # Resample on a one meter depth basis
            #**************************************

            # If the depth is not an integer
            down[self.pres_col] = down[self.pres_col].round(0).astype(int)
            # Drop upward profiles
            down = down.groupby(self.pres_col).first()

            # If there are missing depths
            Xresampled = np.arange(down.index.min(), down.index.max() + 1)
            down = down.reindex(down.index.union(Xresampled)).interpolate().loc[Xresampled]

            #*******************************************
            # Put all the signals together
            #*******************************************

            # If some columns do not exist: the file is regarded as corrupted
            missing_cols = [col for col in self.available_cols if not(col in down.columns)]

            if len(missing_cols) > 0:
                print('Some of the specified columns are missing: ' +\
                      ', '.join(missing_cols) + ',\n so '+ fname + ' is not considered. ' +\
                      'Please compare with existing name:', down.columns)
                continue

            # Get the signals
            signal = down[self.available_cols]

            # If the signal is too short or constant: the file is regarded as corrupted
            if (len(signal) < 3) | (signal.index.max() <= max_depth):
                print(fname + ': depth too short: Not considered as ' +\
                      str(signal.index.max()) + " (the CTD cast max. depth)" +\
                      ' < ' + str(max_depth) + " (the depth range max. you specified).")
                continue

            if ('fluo_col' in self.available_cols):
                if (signal[self.cols['fluo_col']].loc[10:].std() < 1E-4):
                    print('Constant Fluorescence signal:', fname, 'not considered')
                    continue

            # Store the signal
            flc_signals.append(signal.sort_index())

        #===========================================
        # Wrap all signals together
        #===========================================

        if len(flc_signals) == 0:
            station_name = self.station if self.station != None else "Station"
            raise RuntimeError(station_name + ' not taken into account: no valid signal. ' +\
                                'Check the depth of the CTD files' +\
                                ' or the column names you have provided in info_dict')


        if stacked_signals == False:
            return flc_signals

        # Put all signal to the same length
        ranges_start_max = np.max([flc.index[0] for flc in flc_signals])
        ranges_start_max = np.max([ranges_start_max, seq_start])

        ranges_end_min = np.min([flc.index[-1] for flc in flc_signals])
        ranges_end_min = np.min([ranges_end_min, seq_end])

        # Stack all the signals
        flc_signals = [flc.loc[ranges_start_max:ranges_end_min] for flc in flc_signals]
        flc_signals = pd.concat(flc_signals, axis = 1)

        flc_signals.index = range(ranges_start_max, ranges_end_min + 1)
        flc_signals.index.name = 'depth'

        return flc_signals


    def rupture_estimator(self, data, n_bkps):
        '''
        Detect the ruptures in the data

        Parameters
        ----------
        data : pandas DataFrame
            Data for rupture detection.
        n_bkps : int
            The number of breakpoints to look for.

        Returns
        -------
        bkps : list
            The depth of the rupture points.

        '''

        #************************
        # Data scaling
        #************************

        m = data.mean(axis = 0)
        sd = data.std(axis = 0, ddof=0)
        sd = np.where(sd == 0, 1E-16, sd) # Numeric stability
        s_data = (data - m) / sd

        #************************
        # Rupture points
        #************************

        algo = rpt.Binseg(model = "rbf", jump = 1).fit(s_data)
        bkps = algo.predict(n_bkps = n_bkps)
        bkps = np.array(bkps[:-1]).astype(float)
        bkps = bkps + data.index[0] # Take into account the offset

        return bkps


    def rupture_confidence_interval(self, data, n_bkps, depth_range, n_points = 10):
        '''
        Compute rupture estimations for several maximal signal depths and
        returns rupture points as the mean of the estimations along with
        the associated standard error

        Parameters
        ----------
        data : pandas DataFrame
            Data for rupture detection.
        n_bkps : int
            The number of breakpoints to look for.
        depth_range : list
            The range of maximal depths over which the rupture detection is performed.
        n_points : int (default 10)
            The number of maximal depths to try

        Returns : pandas DataFrame
        -------
        The identified boundaries.
        '''

        grid = np.linspace(depth_range[0], depth_range[1], n_points).astype(int)

        bkps = []
        for depth_end in grid:
            bkp = self.rupture_estimator(data.loc[:depth_end], n_bkps)
            bkps.append(bkp)

        means =  np.mean(bkps, axis = 0)
        stds = np.std(bkps, axis = 0)

        bkps = pd.DataFrame(data = np.array([means, stds]).T, columns = ['Mean', 'std'])
        return bkps



    def info_check(self):
        '''
        Performs the checks of information entered by the user

        Returns
        -------
        None.

        '''

        if not(os.path.isdir(self.data_folder)):
            raise ValueError('The specified root directory does not exist (and should):' + self.data_folder)
        if len(os.listdir(self.data_folder)) == 0:
            raise ValueError('The specified root directory contain no files:' + self.data_folder)

        if len(self.ub_range) != 2:
            raise ValueError('ub_range should have two values')
        if len(self.lb_range) != 2:
            raise ValueError('lb_range should have two values')
        if self.pres_col == None:
            raise ValueError('The method need a column containing the pressure info')


    def fit(self):
        '''
        Estimate the boundaries of the active mesopelagic layer

        Returns
        -------
        None.

        '''

        self.info_check()

        #==================================
        # Upper boundary extraction
        #==================================

        self.ub_data = self.format_data([0, self.ub_range[1]])
        upper = self.rupture_confidence_interval(self.ub_data, 1, [self.ub_range[0], self.ub_range[1]])
        upper.columns = ['Upper boundary', 'std Upper boundary']
        self.ub_estim = upper['Upper boundary']
        self.ub_sd =  upper['std Upper boundary']
        self.nb_ctd_ub = self.ub_data.shape[1] // len(self.available_cols)

        #==================================
        # Lower boundary extraction
        #==================================
        
        rounded_upper = int(np.ceil(upper['Upper boundary'][0]))
        self.lb_data = self.format_data([rounded_upper, self.lb_range[1]])
        lower = self.rupture_confidence_interval(self.lb_data, 1, [self.lb_range[0], self.lb_range[1]])
        lower.columns = ['Lower boundary', 'std Lower boundary']
        self.lb_estim = lower['Lower boundary']
        self.lb_sd =  lower['Lower boundary']
        self.nb_ctd_lb = self.lb_data.shape[1] // len(self.available_cols)

        self.boundaries = pd.concat([upper, lower], axis = 1)
        self.is_fitted = True


    def display_boundaries(self):
        '''
        Plot the boundaries found along with the data used to determine them


        Returns
        -------
        fig : matplotlib figure
            The full plot.
        host : matplotlib ax
            The associated ax object.

        '''
        
        if not(self.is_fitted):
            raise RuntimeError('Please fit the model before running this method')
            
        max_depth = self.lb_range[1]
            
        # Define the colors 
        eupho_color = 'lightgray'
        meso_color = 'slategrey'

        n_curves = len(self.available_cols)
        rpts = [self.ub_estim[0], self.lb_estim[0]]

        pars = {}  
        pps = {}

        fig, host = plt.subplots(figsize=(4,12)) # (width, height) in inches
          
        host.set_xlim(0, 2)
        host.set_ylim(0, max_depth)
        host.axhspan(0, rpts[0], facecolor = eupho_color, alpha=0.3, label = 'Upper zone')
        host.axhspan(rpts[0], rpts[1], facecolor = meso_color, alpha=0.3, label = 'Active mesopelagic zone')
        host.set_title(self.station, fontsize = 16) 

        # Plot Upper and Lower Boundaries data
        host.plot(self.ub_data[self.available_cols[0]], self.ub_data.index,\
                                 color = self.available_colors[0])
            
        line2D = host.plot(self.lb_data[self.available_cols[0]], self.lb_data.index,\
                                 color = self.available_colors[0])
        if len(line2D) > 1:
            line2D = [line2D[0]]

        pps['host'], = line2D
        host.tick_params(axis='x', colors = pps['host'].get_color())
        host.xaxis.label.set_color(pps['host'].get_color())
        host.set_xlabel(self.available_aliases[0], fontsize = 11)

        for i in range(n_curves):    
            pars['p' + str(i)] = host.twiny()
            pars['p' + str(i)].xaxis.set_label_position('bottom') 
            pars['p' + str(i)].xaxis.tick_bottom()
            pars['p' + str(i)].spines['bottom'].set_position(('outward', 35 + 40 * i))

           
        for i in range(1, n_curves):    
            # Plot Upper and Lower Boundaries data
            pars['p' + str(i)].plot(self.ub_data[self.available_cols[i]],\
                                                         self.ub_data.index,\
                                                         color=self.available_colors[i])
                
            line2D = pars['p' + str(i)].plot(self.lb_data[self.available_cols[i]],\
                                                         self.lb_data.index,\
                                                         color=self.available_colors[i])
            if len(line2D) > 1:
                line2D = [line2D[0]]
                
            pps['p' + str(i)], = line2D
            pars['p' + str(i)].set_ylim(1, max_depth)
            pars['p' + str(i)].xaxis.label.set_color(pps['p' + str(i)].get_color())
            pars['p' + str(i)].tick_params(axis='x', colors = pps['p' + str(i)].get_color())
            pars['p' + str(i)].set_xlabel(self.available_aliases[i], fontsize = 11)

        host.invert_yaxis()
        host.legend(['Upper zone', 'Active mesopelagic zone'])
        fig.tight_layout()
        plt.show()
        
        return fig, host
    
    def sensitivity_analysis(self):
        '''
        Plot the sensitivity of the boundaries to the withdrawal of each variable

        Returns
        -------
        fig : matplotlib figure
            The full plot.
        axs : matplotlib ax
            The associated axes objects.

        '''
        
        if not(self.is_fitted):
            raise RuntimeError('Please fit the model before running this method')
            
        ub_ref = self.ub_estim[0]
        lb_ref = self.lb_estim[0]

        ub_holdout = pd.DataFrame()
        lb_holdout = pd.DataFrame()
        n_curves = len(self.available_cols)

        for col, col_alias in zip(self.available_cols, self.available_aliases):
            
            #===============================
            # Upper boundary sensitivity
            #===============================
            
            ub_data = self.ub_data
            hold_out_one_var = ub_data.loc[:,~ub_data.columns.isin([col])]
            ub = self.rupture_confidence_interval(hold_out_one_var, 1, self.ub_range)
            ub.index = [col_alias]
            ub_holdout = pd.concat([ub_holdout, ub])

            #===============================
            # Lower boundary sensitivity
            #===============================   
            
            lb_data = self.lb_data
            hold_out_one_var = lb_data.loc[:,~lb_data.columns.isin([col])]
            lb = self.rupture_confidence_interval(hold_out_one_var, 1, self.lb_range)
            lb.index = [col_alias]
            lb_holdout = pd.concat([lb_holdout, lb])
        
        #===============================
        # Wrap up
        #===============================   
            
        delta_ub = ((ub_ref - ub_holdout[['Mean']]) / ub_ref).abs().T
        delta_lb = ((lb_ref - lb_holdout[['Mean']]) / lb_ref).abs().T

        upper_delta = (delta_ub.iloc[0] * 100).tolist()
        lower_delta = (delta_lb.iloc[0] * 100).tolist()

        fig, axs = plt.subplots(2, 1, figsize=(7, 5), sharex=True)
        axs[0].bar(range(n_curves), upper_delta, color = self.available_colors) 
        axs[0].set_title('a) Mesopelagic upper boundary')
        axs[0].set_ylabel("Variation (%)")

        axs[1].bar(range(n_curves), lower_delta, color = self.available_colors) 
        axs[1].set_title('b) Mesopelagic lower boundary')
        axs[1].set_ylabel("Variation (%)")
        axs[1].set_xticks(range(n_curves), delta_lb.columns)

        plt.tight_layout()
        plt.show()
        
        return fig, axs

