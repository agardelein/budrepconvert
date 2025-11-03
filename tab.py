#!/home/arnaud/venv/bin/python3

import re
import locale
import tabula
import numpy as np
import pandas as pd
import unittest
import tomllib

WRITE_REFERENCE_FILES = True

class BaseView:
    def __init__(self, filename, config):
        self.data = None
        self.labels_to_fix = {}
        self.data_to_fix = {}
        self.config = config
        self.header_lines = 1
        self.table_number = 1
        self.pages = None
        self.data_start_column = 2
        self.initial_chapter_name_column = 1
        self.filename = filename
        self.axis = 0
        self.verbose = False
        self.chapter_number_mixed_with_name = False
        self.update_config(config)
        if isinstance(self.pages, int):
            self.read_singlepage_table(self.filename, self.pages)
        else:
            self.read_multipage_table(self.filename, self.pages, self.axis)

    def update_config(self, config):
        self.header_lines = config.get('header_lines', self.header_lines)
        self.data_start_column = config.get('data_start_column', self.data_start_column)
        self.initial_chapter_name_column = config.get('initial_chapter_name_column', self.initial_chapter_name_column)
        self.data_to_fix = config.get('data_to_fix', self.data_to_fix)
        self.labels_to_fix = config.get('labels_to_fix', self.labels_to_fix)
        if isinstance(self.data_to_fix, list):
            self.data_to_fix = {(k[0], k[1]): v for k, v in self.data_to_fix}
        self.table_number = config.get('table_number', self.table_number)
        self.pages = config.get('pages', self.pages)
        self.filename = config.get('filename', self.filename)
        self.axis = config.get('axis', self.axis)
        self.verbose = config.get('verbose', self.verbose)
        self.chapter_number_mixed_with_name = config.get('chapter_number_mixed_with_name', self.chapter_number_mixed_with_name)
            
    def read_singlepage_table(self, filename, page):
        self.update_config(self.config.get(str(page), {}))
        self.read_data(filename, page, self.table_number)
        self.print_if_verbose('*-', 'After read_data')
        
        if self.chapter_number_mixed_with_name:
            self.extract_chapter_numbers()
        self.convert_header_to_labels()
        self.print_if_verbose('*/', 'After convert_header_to_labels')
        
        self.merge_multilines_cells()
        self.remove_notes_from_chapter_names()
        self.delete_useless_columns()
        self.fix_data()
        self.print_if_verbose('*.', 'After fix_data')
        
        self.convert_first_col_to_string()
        self.convert_data()
        self.print_if_verbose('*+', 'After convert_data')

    def read_multipage_table(self, filename, pages, axis):
        data = None
        for page in pages:
            if isinstance(page, list):
                self.read_multipage_table(filename, page, 'index')
            else:
                self.read_singlepage_table(filename, page)
            if data is None:
                data = self.data
                self.table_number = 0
            else:
                if axis in [0, 'index']:
                    data = pd.concat([data, self.data], axis=axis,
                                     ignore_index=True)
                else:
                    data = pd.concat([data, self.data.iloc[:,2:]], axis=axis,
                                     )
        self.data = data
        self.print_if_verbose('/-', 'After concat')

    def read_data(self, filename, page, table_number):
        df = tabula.read_pdf(filename,
                             pages=page,
                             stream=True,
                             pandas_options={'header': None},
                             )
        self.data = df[table_number]

    def convert_header_to_labels(self):
        drop_list = list(range(self.header_lines))
        names = {}
        for i, col in self.data.items():
            s = ' '.join(self.merge_header_cells(col)).title()
            names[i] = self.remove_notes(s)
        names = self.fix_labels(names)
        self.data.rename(columns=names, inplace=True)
        self.data.drop(drop_list, inplace=True)
        self.data.reset_index(drop=True, inplace=True)

    def fix_labels(self, names):
        for i, label in self.labels_to_fix.items():
            if label == 'nan':
                names[int(i)] = np.nan
            else:
                names[int(i)] = label
        return names

    def merge_header_cells(self, cells):
        return cells[:self.header_lines].dropna().astype(str)
    
    def merge_multilines_cells(self):
        drop_list = []
        self.data.dropna(how='all', inplace=True, ignore_index=True)
        self.print_if_verbose('---', 'After dropna')
        for i, line in self.data.iterrows():
            if self.line_has_no_data(line):
                self.merge_with_previous_line(i)
                drop_list.append(line.name)
        self.data.drop(drop_list, inplace=True)        
        self.data.reset_index(drop=True, inplace=True)

    def line_has_no_data(self, line):
        a = line.iloc[self.data_start_column:].dropna()
        return a.empty
    
    def merge_with_previous_line(self, num):
        col = self.initial_chapter_name_column
        part1 = self.data.iloc[num - 1, col].strip()
        part2 = self.data.iloc[num, col].strip()
        self.data.iloc[num - 1, col] = part1 + " " + part2
        
    def remove_notes_from_chapter_names(self):
        col = self.initial_chapter_name_column
        r = self.data.iloc[:, col].apply(self.remove_notes)
        self.data.iloc[:, col] = r

    def remove_notes(self, s):
        if not isinstance(s, str):
            return s
        else:
            return re.sub(r'\(\d+\)', '', s).strip()

    def delete_useless_columns(self):
        if np.nan in self.data.columns:
            self.data.drop(columns=[np.nan], inplace=True)

    def fix_data(self):
        for k, v in self.data_to_fix.items():
            self.data.loc[k] = v
    
    def convert_data(self):
        def fun(s):
            if not isinstance(s, str):
                return s
            rep = s.replace(' ', '').replace(',', '.')
            try:
                return float(rep)
            except ValueError:
                return s

        dataset = self.data.iloc[:, self.data_start_column:]
        self.data.iloc[:,self.data_start_column:] = dataset.map(fun)
        self.data = self.data.convert_dtypes(convert_integer=False)

    def convert_first_col_to_string(self):
        self.data = self.data.astype({'Chapitre': str})
        
    def extract_chapter_numbers(self):
        nums= pd.Series(["" for x in range(self.data[0].size)])
        names = pd.Series(["" for x in range(self.data[0].size)])
        for i, s in enumerate(self.data[0]):
            s = self.remove_notes(s)
            nums[i] = self.find_chapter_number(s)
            s = self.remove_chapter_number(s)
            names[i] = self.find_chapter_name(s)
        self.data.drop(0, axis=1, inplace=True)
        c = self.data.columns
        self.data.rename(columns=lambda x: x + 1, inplace=True)
        self.data = pd.concat([nums, names, self.data], axis=1)

    def find_chapter_number(self, s):
        if not isinstance(s, str):
            return s
        m = re.match(r'^(\d+)', s)
        if m is None:
            return np.nan
        return m.groups()[0]

    def find_chapter_name(self, s):
        if not isinstance(s, str):
            return s
        return s.strip()

    def remove_chapter_number(self, s):
        if not isinstance(s, str):
            return s
        return re.sub(r'^(\d+)', '', s)

    def print_if_verbose(self, pattern='', comment=''):
        if self.verbose:
            print(pattern * 20, comment)
            print(self.data)
            print(self.data.dtypes)
        
with open('config.toml', 'rb') as f:
    conf = tomllib.load(f)
filename = conf['general']['filename']

for table in conf['general']['tables']:
    ct = conf[table]
    c = BaseView(filename, ct)
    if WRITE_REFERENCE_FILES:
        c.data.to_csv(table + '.csv', float_format='%.2f', index=False)

print('-'*50, 'Done')

class test_bg(unittest.TestCase):

    def setUp(self):
        with open('config.toml', 'rb') as f:
            config = tomllib.load(f)
        self.config = config
        self.filename = conf['general']['filename']
    
    def convert_data(self, data):
        data = data.astype({'Chapitre': str})
        return data.convert_dtypes(convert_integer=False)

    def _test_table(self, table, show=False):
        act = BaseView(self.filename, self.config[table]).data
        ref = pd.read_csv(table + '-reference.csv')
        self._test_equals(act, ref, show)

    def _test_equals(self, act, ref, show=False):
        actual = self.convert_data(act)        
        reference = self.convert_data(ref)
        if show:
            print('/'*40)
            print(actual)
            print(reference)
            print(actual.dtypes)
            print(reference.dtypes)
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

    def test_multipage_table_4ways(self):
        self._test_table('pcvei')

if __name__ == '__main__':
    unittest.main()
