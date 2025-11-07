#!/home/arnaud/venv/bin/python3

import re
import tabula
import numpy as np
import pandas as pd

class SinglePageTable:
    def __init__(self, filename, config):
        self.data = None
        self.labels_to_fix = {}
        self.data_to_fix = {}
        self.swap_labels_to_column = []
        self.config = config
        self.header_lines = 1
        self.table_number = 1
        self.pages = None
        self.data_start_column = 2
        self.initial_chapter_name_column = 1
        self.axis = 'index'
        self.verbose = False
        self.chapter_number_mixed_with_name = False
        self.mask_header_cells = []
        self.split_column_data = {}
        self.update_config(config)
        self.read_singlepage_table(filename, self.pages)

    def update_config(self, config):
        self.header_lines = config.get('header_lines', self.header_lines)
        self.data_start_column = config.get('data_start_column',
                                            self.data_start_column)
        self.initial_chapter_name_column = config.get('initial_chapter_name_column', self.initial_chapter_name_column)
        self.data_to_fix = config.get('data_to_fix', self.data_to_fix)
        self.labels_to_fix = config.get('labels_to_fix',
                                        self.labels_to_fix)
        if isinstance(self.data_to_fix, list):
            self.data_to_fix = {(k[0], k[1]): v for k, v in self.data_to_fix}
        self.swap_labels_to_column = config.get('swap_labels_to_column',
                                                self.swap_labels_to_column)
        self.table_number = config.get('table_number', self.table_number)
        self.pages = config.get('pages', self.pages)
        self.axis = config.get('axis', self.axis)
        self.verbose = config.get('verbose', self.verbose)
        self.chapter_number_mixed_with_name = config.get('chapter_number_mixed_with_name',self.chapter_number_mixed_with_name)
        self.mask_header_cells = config.get('mask_header_cells',
                                            self.mask_header_cells)
        self.split_column_data = config.get('split_column_data',
                                            self.split_column_data)
            
    def read_singlepage_table(self, filename, page):
        self.update_config(self.config.get(str(page), {}))
        self.read_data(filename, page, self.table_number)
        self.print_if_verbose('*-', 'After read_data')
        
        if self.chapter_number_mixed_with_name:
            self.extract_chapter_numbers()
        self.mask_cells()
        self.split_columns()
        self.convert_header_to_labels()
        self.print_if_verbose('*/', 'After convert_header_to_labels')
        
        self.merge_multilines_cells()
        self.remove_notes_from_chapter_names()
        self.delete_useless_columns()
        self.fix_data()
        self.print_if_verbose('*.', 'After fix_data')
        
        self.convert_first_col_to_index()
        self.convert_data()
        self.print_if_verbose('*+', 'After convert_data')

    def read_data(self, filename, page, table_number):
        df = tabula.read_pdf(filename,
                             pages=page,
                             stream=True,
                             pandas_options={'header': None},
                             )
        self.data = df[table_number]

    def split_columns(self):
        for source, dest in self.split_column_data.items():
            for line in range(self.header_lines, self.data.shape[0]):
                s = self.data.loc[line, int(source)].split()
                self.data.loc[line, dest[0]:dest[1]] = s
        
    def convert_header_to_labels(self):
        drop_list = list(range(self.header_lines))
        names = {}
        for i, col in self.data.items():
            s = ' '.join(self.merge_header_cells(col)).title()
            names[i] = self.remove_notes(s)
        names = self.swap_labels_and_column(names)
        names = self.fix_labels(names)
        self.data.rename(columns=names, inplace=True)
        self.data.drop(drop_list, inplace=True)
        self.data.reset_index(drop=True, inplace=True)

    def mask_cells(self):
        for coords in self.mask_header_cells:
            c1 = coords[0]
            c2 = coords[1]
            if c1[0] == c2[0] and c1[1] == c2[1]:
                self.data.loc[c1[0],c1[1]] = np.nan
            elif c1[0] == c2[0] and c1[1] != c2[1]:
                self.data.loc[c1[0],c1[1]:c2[1]] = np.nan
            elif c1[0] != c2[0] and c1[1] == c2[1]:
                self.data.loc[c1[0]:c2[0],c1[1]] = np.nan
            else:
                self.data.loc[c1[0]:c2[0],c1[1]:c2[1]] = np.nan
        
    def fix_labels(self, names):
        if 0 not in self.labels_to_fix.keys():
            self.labels_to_fix[0] = 'Chapitre'
        for i, label in self.labels_to_fix.items():
            if label == 'nan':
                names[int(i)] = np.nan
            else:
                names[int(i)] = label
        return names

    def swap_labels_and_column(self, names):
        for source, dest in self.swap_labels_to_column:
            names[dest] = names[source]
            names[source] = np.nan
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

    def convert_first_col_to_index(self):
        index= pd.Series(["" for x in range(self.data.shape[0])])
        for i in range(self.data.iloc[:,0].size):
            value = self.data.iloc[i, 0]
            if isinstance(value, str):
                index.iloc[i] = value
            elif np.isnan(value):
                index.iloc[i] = self.data.iloc[i, 1]
                self.data.iloc[i, 1] = ''
            else:
                index.iloc[i] = self.to_integer_string(value)
                
        index.convert_dtypes()
        self.data.index = index
        self.data.drop('Chapitre', axis=1, inplace=True)
        self.data_start_column = self.data_start_column - 1

    def to_integer_string(self, value):
        return f'{int(value):d}'
        
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
            print(pattern * 20, comment, 'p.', self.pages)
            print(self.data)
            print(self.data.dtypes)

class MultiPageTable:
    def __init__(self, filename, config):
        self.data = None
        self.config = config
        self.pages = None
        self.axis = 'index'
        self.verbose = False
        self.update_config(self.config)
        self.read_multipage_table(filename, self.pages, self.axis)

    def update_config(self, config):
        self.pages = config.get('pages', self.pages)
        self.axis = config.get('axis', self.axis)
        self.verbose = config.get('verbose', self.verbose)

    def read_multipage_table(self, filename, pages, axis):
        data = None
        for page in pages:
            if data is not None:
                self.add_to_page_config(page, 'table_number', 0)
                self.config[str(page)]['table_number'] = 0
            config = self.config.copy()
            config['pages'] = page
            if isinstance(page, list):
                config['axis'] = 'index'
                tab = MultiPageTable(filename, config)
            else:
                tab = SinglePageTable(filename, config)
            if data is None:
                data = tab.data
            else:
                if axis in [0, 'index']:
                    data = pd.concat([data, tab.data], axis=axis)
                else:
                    data = pd.concat([data, tab.data.iloc[:,2:]],
                                     axis=axis)
        self.data = data
        self.print_if_verbose('/-', 'After concat')

    def add_to_page_config(self, page, key, value):
        page = str(page)
        if page not in self.config.keys():
            self.config[page] = {}
        self.config[page][key] = value
        
    def print_if_verbose(self, pattern='', comment=''):
        if self.verbose:
            print(pattern * 20, comment, 'p.', self.pages)
            print(self.data)
            print(self.data.dtypes)

def read_from_config(filename, ct):
    pages = ct['pages']
    if isinstance(pages, int):
        data = SinglePageTable(filename, ct).data
    else:
        data = MultiPageTable(filename, ct).data
    return data
