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
from seabird.cnv import fCNV
from sklearn.preprocessing import StandardScaler

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
        
        self.ub_range = info_dict['ub_range'] # upper bound range
        self.lb_range = info_dict['lb_range'] # lower bound range
        self.cruise = info_dict['cruise_name'] 
        self.station = info_dict['station_name']
        
        self.pres_col = info_dict['pres_col']
        
        self.cols = {}
        for col in ['fluo_col', 'oxygen_col', 'temp_col', 'salinity_col', 'density_col']:
            self.cols[col] = info_dict[col]
        
        # Keep only the columns existing in the files 
        self.available_cols = [colname for col_alias, colname in self.cols.items()\
                               if colname != None]
            
        self.sep = info_dict['sep']
        self.files_format = info_dict['files_format']
        self.data_folder = info_dict['data_folder']
              
    
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
            raise RuntimeError('No files in the folder' + folder)
    
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
            down[self.pres_col] = down[self.pres_col].round(0)
            # Drop upward profiles
            down = down.groupby(self.pres_col).first().reset_index()
            
            # If there are missing depths
            Xresampled = np.arange(down.index.min(), down.index.max() + 1)
            down = down.reindex(down.index.union(Xresampled)).interpolate().loc[Xresampled]
                                           
            #*******************************************
            # Put all the signals together
            #*******************************************
            
            
            # If some columns do not exist: the file is regarded as corrupted
            if not(np.all(pd.Series(self.available_cols).isin(down.columns))):
                continue
            
            # Get the signals
            signal = down[self.available_cols]
            
            # If the signal is too short or constant: the file is regarded as corrupted
            if (len(signal) < 3) | (len(signal) <= max_depth): 
                continue
            
            if ('fluo_col' in self.available_cols): 
                if (signal[self.cols['fluo_col']].loc[10:].std() < 1E-4):
                    continue
            
            # Store the signal        
            flc_signals.append(signal.sort_index())
    
        #===========================================
        # Wrap all signals together
        #===========================================
          
        if len(flc_signals) == 0:
            print(self.station, ' not taken into account: no valid signal')
            raise RuntimeError(self.station + 'not taken into account: no valid signal.\
                                Check the CTD files or the column names you have provided in info_dict')

            #return pd.DataFrame([])
        
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
        
        ss = StandardScaler()
        s_data = ss.fit_transform(data)
        
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
    
        Returns
        -------
        None.
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
        # Euphotic extraction
        #==================================
    
        self.ub_data = self.format_data([0, self.ub_range[1]])        
        eupho = self.rupture_confidence_interval(self.ub_data, 1, [self.ub_range[0], self.ub_range[1]])
        eupho.columns = ['Euphotic end', 'std Euphotic end']
        self.ub_estim = eupho['Euphotic end']
        self.ub_sd =  eupho['std Euphotic end']
        self.nb_ctd_ub = self.ub_data.shape[1] // len(self.available_cols)
                
        #==================================
        # Mesopelagic extraction
        #==================================

        self.lb_data = self.format_data([eupho['Euphotic end'][0], self.lb_range[1]])
        meso = self.rupture_confidence_interval(self.lb_data, 1, [self.lb_range[0], self.lb_range[1]])
        meso.columns = ['Mesopelagic end', 'std Mesopelagic end']
        self.lb_estim = meso['Mesopelagic end']
        self.lb_sd =  meso['std Mesopelagic end']
        self.nb_ctd_lb = self.lb_data.shape[1] // len(self.available_cols)
        
        self.boundaries = pd.concat([eupho, meso], axis = 1)