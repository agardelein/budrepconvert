#!/home/arnaud/venv/bin/python3

import re
import tabula
import numpy as np
import pandas as pd

class SinglePageTable:
    def __init__(self, filename, config, only_read=False):
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
        self.rebuild_data = {}
        self.data_in_first_column = []
        self.update_config(config)
        self.read_singlepage_table(filename, self.pages, only_read)

    def update_config(self, config):
        self.header_lines = config.get('header_lines', self.header_lines)
        self.data_start_column = config.get('data_start_column',
                                            self.data_start_column)
        self.initial_chapter_name_column = config.get('initial_chapter_name_column', self.initial_chapter_name_column)
        self.data_to_fix = config.get('data', self.data_to_fix)
        self.labels_to_fix = config.get('labels',
                                        self.labels_to_fix)
        if isinstance(self.data_to_fix, list):
            self.data_to_fix = {(k[0], k[1]): v for k, v in self.data_to_fix}
        self.swap_labels_to_column = config.get('move_labels',
                                                self.swap_labels_to_column)
        self.table_number = config.get('table_number', self.table_number)
        self.pages = config.get('pages', self.pages)
        self.axis = config.get('axis', self.axis)
        self.verbose = config.get('verbose', self.verbose)
        self.chapter_number_mixed_with_name = config.get('chapter_number_mixed_with_name',self.chapter_number_mixed_with_name)
        self.mask_header_cells = config.get('header_mask',
                                            self.mask_header_cells)
        self.rebuild_data = config.get('rebuild_data', self.rebuild_data)
        self.data_in_first_column = config.get('data_in_first_column', self.data_in_first_column)

    def read_singlepage_table(self, filename, page, only_read):
        self.update_config(self.config.get(str(page), {}))
        if self.chapter_number_mixed_with_name:
            self.initial_chapter_name_column = 0
        self.read_data(filename, page, self.table_number)
        self.print_if_verbose('*-', f'After read_data Table {self.table_number}')
        if only_read:
            return

        self.convert_header_to_labels()
        self.print_if_verbose('*/', 'After convert_header_to_labels')

        self.merge_multilines_cells()
        if self.chapter_number_mixed_with_name:
            self.extract_chapter_numbers()
            self.print_if_verbose('*_', 'After extract_chapter_number')

        self.print_if_verbose('*#', 'After merge_multilines_cells')
        self.remove_notes_from_chapter_names()
        self.fix_data()
        self.print_if_verbose('*.', 'After fix_data')
        
        self.convert_first_col_to_index()
        self.convert_data()
        self.print_if_verbose('*+', 'After convert_data')

    def read_data(self, filename, page, table_number):
        df = tabula.read_pdf(filename,
                             pages=page,
                             stream=True,
                             pandas_options={'header': None, 'dtype':str},
                             )
        self.data = df[table_number]

    def convert_header_to_labels(self):
        self.mask_cells()
        drop_list = list(range(self.header_lines))
        names = {}
        for i, col in self.data.items():
            s = self.merge_header_cells(col)
            names[i] = self.remove_notes(s)
        names = self.swap_labels_and_column(names)
        names = self.fix_labels(names)
        self.data.rename(columns=names, inplace=True)
        self.data.drop(drop_list, inplace=True)
        self.data.reset_index(drop=True, inplace=True)
        for name in names.values():
            if name not in list(self.data.columns):
                self.data[name] = self.data.iloc[:,-1]
                self.data[name] = self.data[name].astype(str)
                self.data[name] = self.data[name].apply(lambda x: '')
        if self.data_in_first_column:
            self.extract_data_from_first_column()
        self.delete_useless_columns()

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

    def extract_data_from_first_column(self):
        data = self.data.iloc[:, 0]
        data = data.apply(self.split_chapter_and_data)
        data = data.map(str.strip)
        column_names = [self.data.columns[0]]
        column_names.extend(self.data_in_first_column)
        data.columns = column_names
        self.data.drop(columns=self.data.columns[0], inplace=True, axis='columns')
        self.data = pd.concat([data, self.data], axis='columns')

    def split_chapter_and_data(self, s):
        elements = re.split(r'((\d{1,3} )*\d+,\d\d)+', s)
        chapter = elements.pop(0)
        values = list(filter(lambda x: isinstance(x, str) and ',' in x, elements))
        res = [chapter]
        res.extend(values)
        return pd.Series(res)
        
    def fix_labels(self, names):
        if 0 not in self.labels_to_fix.keys():
            self.labels_to_fix[0] = 'Chapitre'
        for i, label in self.labels_to_fix.items():
            if label == 'nan':
                names[int(i)] = np.nan
            else:
#                names[int(i)] = label.title()
                names[int(i)] = label
        return names

    def swap_labels_and_column(self, names):
        for source, dest in self.swap_labels_to_column:
            names[dest] = names[source]
            names[source] = np.nan
        return names

    def merge_header_cells(self, cells):
        return ' '.join(cells[:self.header_lines].dropna().astype(str)).title()
    
    def merge_multilines_cells(self):
        drop_list = []
        self.data.dropna(how='all', inplace=True, ignore_index=True)
        self.print_if_verbose('---', 'After dropna')
        for num, line in self.data.iterrows():
            if self.is_multirow(num, line):
                l = self.merge_with_previous_line(num, line)
                self.data.iloc[num - 1, :] = l
                drop_list.append(line.name)
        self.data.drop(drop_list, inplace=True)        
        self.data.reset_index(drop=True, inplace=True)

    def is_multirow(self, num, line):
        if self.has_no_data(line):
            return True
        else:
            if num and self.preceding_row_has_truncated_numbers(num):
                return True

    def has_no_data(self, line):
        fun = lambda cell: np.nan if isinstance(cell, str) and not cell else cell
        a = line.iloc[self.data_start_column:].apply(fun).dropna()
        return a.empty

    def preceding_row_has_truncated_numbers(self, current_index):
        preceding_index = current_index - 1
        fun = lambda cell: isinstance(cell, str) and cell and\
            ',' not in cell
        df = self.data.iloc[preceding_index, self.data_start_column:]
        return df.apply(fun).any()
    
    def merge_with_previous_line(self, num, line):
        fun_a = lambda x: x.apply(self.prepare_for_merge, args=(True,))
        fun_b = lambda x: x.apply(self.prepare_for_merge, args=(False,))
        
        df = self.data.iloc[num - 1:num + 1, :]
        dfa = df.iloc[:, :self.data_start_column].apply(fun_a)
        dfb = df.iloc[:, self.data_start_column:].apply(fun_b)
        sa = dfa.aggregate(' '.join).apply(str.strip)
        sb = dfb.aggregate(''.join).apply(str.strip)
        line = pd.concat([sa, sb])
        return line

    def prepare_for_merge(self, cell, float_to_int):
        if isinstance(cell, float) and np.isnan(cell):
            return ''
        elif isinstance(cell, float):
            return str(int(cell)) if float_to_int else str(cell)
        else:
            return cell
        
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
            v = np.nan if v == 'nan' else v
            self.data.loc[k] = v
        if self.rebuild_data:
            self.print_if_verbose('_/', 'Before rebuild_line_data')
            self.rebuild_line_data()

    def rebuild_line_data(self):
        for i, row in self.data.iloc[:, 2:].iterrows():
            s = self.cleaned_row_as_string(row)
            r = self.split_numbers(s)
            l = self.filter_none_and_integer_values(r)
            if l:
                self.data.iloc[i, 2:] = l
        self.print_if_verbose('#', 'After rebuild_line_data')

    def cleaned_row_as_string(self, row):
        return ' '.join(row.dropna())

    def split_numbers(self, s):
        return re.split(r'((\d{1,3} )*\d+,\d\d)', s)

    def filter_none_and_integer_values(self, r):
        return list(filter(lambda x: x is not None and ',' in x, r))
    
    def convert_data(self):
        def fun(s):
            if not isinstance(s, str):
                return s
            rep = s.replace(' ', '').replace(',', '.')
            if not s:
                return np.nan
            try:
                return float(rep)
            except ValueError:
                return s
        dataset = self.data.iloc[:, self.data_start_column:]
        self.data.iloc[:,self.data_start_column:] = dataset.map(fun)
        self.data.dropna(inplace=True, how='all')
        self.data = self.data.convert_dtypes(convert_integer=False)

    def convert_first_col_to_index(self):
        index= pd.Series(["" for x in range(self.data.shape[0])])
        for i in range(self.data.iloc[:,0].size):
            value = self.data.iloc[i, 0]
            if isinstance(value, str) and value:
                index.iloc[i] = value
            elif (isinstance(value, str) and not value) or np.isnan(value):
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
        size = self.data.iloc[:, 0].size
        nums= pd.Series(["" for x in range(size)])
        names = pd.Series(["" for x in range(size)])

        for i, s in enumerate(self.data.iloc[:,0]):
            s = self.remove_notes(s)
            nums[i] = self.find_chapter_number(s)
            s = self.remove_chapter_number(s)
            names[i] = self.find_chapter_name(s)
        self.data.drop(columns=self.data.columns[0], axis=1, inplace=True)
        df = pd.DataFrame({'Chapitre':nums, 'Libellé':names})
        self.data = pd.concat([df, self.data], axis=1)

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
    def __init__(self, filename, config, only_read):
        self.data = None
        self.config = config
        self.pages = None
        self.axis = 'index'
        self.verbose = False
        self.update_config(self.config)
        self.read_multipage_table(filename, self.pages, self.axis, only_read)

    def update_config(self, config):
        self.pages = config.get('pages', self.pages)
        self.axis = config.get('axis', self.axis)
        self.verbose = config.get('verbose', self.verbose)

    def read_multipage_table(self, filename, pages, axis, only_read):
        data = None
        for page in pages:
            if data is not None:
                self.add_to_page_config(page, 'table_number', 0)
            config = self.config.copy()
            config['pages'] = page
            if isinstance(page, list):
                config['axis'] = 'index'
                tab = MultiPageTable(filename, config, only_read)
            else:
                tab = SinglePageTable(filename, config, only_read)
            if data is None:
                data = tab.data
            else:
                if axis in [0, 'index']:
                    data = pd.concat([data, tab.data], axis=axis)
                else:
                    data = pd.concat([data, tab.data.iloc[:,1:]],
                                     axis=axis)
        self.data = data
        if only_read:
            return
        self.print_if_verbose('/-', 'After concat')

    def add_to_page_config(self, page, key, value):
        page = str(page)
        if page not in self.config.keys():
            self.config[page] = {}
        self.config[page][key] = self.config[page].get(key, value)
        
    def print_if_verbose(self, pattern='', comment=''):
        if self.verbose:
            print(pattern * 20, comment, 'p.', self.pages)
            print(self.data)
            print(self.data.dtypes)

def read_from_config(filename, ct, only_read=False):
    pages = ct['pages']
    if isinstance(pages, int):
        data = SinglePageTable(filename, ct, only_read).data
    else:
        data = MultiPageTable(filename, ct, only_read).data
    return data
