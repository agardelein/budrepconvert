#!/home/arnaud/venv/bin/python3

import numpy as np
import pandas as pd
import unittest
import tomllib
from budget_report import read_from_config

with open('config.toml', 'rb') as f:
    conf = tomllib.load(f)
filename = conf['general']['filename']

class test_bg(unittest.TestCase):

    def setUp(self):
        with open('config.toml', 'rb') as f:
            config = tomllib.load(f)
        self.config = config
        self.filename = conf['general']['filename']
    
    def convert_data(self, data, show=False):
        for i, v in enumerate(data.iloc[:,0]):
            if not isinstance(v, str) and \
               (isinstance(v, pd._libs.missing.NAType) or np.isnan(v)):
                    data.iloc[i, 0] = ''
        return data.convert_dtypes(convert_integer=False)

    def _test_table(self, table, show=False):
        act = read_from_config(self.filename, self.config[table])
        ref = pd.read_csv(table + '-reference.csv', index_col=0)
        self._test_equals(act, ref, show)

    def _test_equals(self, act, ref, show=False):
        actual = self.convert_data(act, show)        
        reference = self.convert_data(ref, show)
        if show:
            print('/'*40)
            print(actual)
            print(reference)
            print(actual.dtypes)
            print(reference.dtypes)
            print(actual.index)
            print(reference.index)
        return self.assertTrue(actual.equals(reference))
    
    def test_balance_generale_depenses_invest(self):
        self._test_table('bgdi')

    def test_balance_generale_depenses_fonct(self):
        self._test_table('bgdf')

    def test_balance_generale_recettes_invest(self):
        self._test_table('bgri')

    def test_balance_generale_recettes_fonct(self):
        self._test_table('bgrf')

    def test_vue_ensemble_depenses(self):
        self._test_table('vedi')
        
    def test_vue_ensemble_recettes(self):
        self._test_table('veri')

    def test_detail_par_article(self):
        self._test_table('dadi')
        self._test_table('dari')
       
    def test_multipage_table(self):
        self._test_table('dadf')
        self._test_table('darf')

    def test_multipage_table_4ways(self):
        self._test_table('pcvei')

    def test_multipage_header_mask_and_columns_split(self):
        self._test_table('f0-sg')

    def test_multipage_header_mask_columns_split_multirows(self):
        self._test_table('f2')

    def test_data_in_first_column(self):
        self._test_table('f5')

if __name__ == '__main__':
    unittest.main()
