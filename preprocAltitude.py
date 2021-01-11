#!/usr/bin/env python
import sys, re
from math import isnan

class preprocAltitude():

    def __init__(self, alpha):
        self.alpha = alpha
           
    def exp_wgt_smoothing(self):
        
        if isnan(self.new_alt) and not isnan(self.prior_alt):
            self.smoothed_alt = self.prior_alt
        elif not isnan(self.new_alt) and isnan(self.prior_alt):
            self.smoothed_alt = self.new_alt
        elif isnan(self.new_alt) and isnan(self.prior_alt):
            self.smoothed_alt = nan
        else: 
            self.smoothed_alt = self.prior_alt + self.alpha * (self.new_alt - self.prior_alt)

    def update_alt_smoother(self, new_alt, prior_alt):

        try:
            self.new_alt = float(new_alt)
        except ValueError:
            self.new_alt = nan

        try:
            self.prior_alt = float(prior_alt)
        except ValueError:
            self.prior_alt = self.new_alt

        self.exp_wgt_smoothing()

    def get_new_alt(self):
        return self.smoothed_alt

    def get_alt_src(self):
        self.source = 'Altimeter'
        return self.source
