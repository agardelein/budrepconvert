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
    def __init__(self, filename=None, pages=None, table_number=1, axis=0,
                 header_lines=None,
                 labels_to_fix={},
                 data_to_fix={},
                 config={}):
        self.data = None
        self.labels_to_fix = labels_to_fix
        self.data_to_fix = data_to_fix
        self.config = config
        self.header_lines = header_lines
        self.table_number = table_number
        self.pages = pages
        self.filename = filename
        self.update_config(config)
        if isinstance(self.pages, int):
            self.read_singlepage_table(self.filename, self.pages)
        else:
            self.read_multipage_table(self.filename, self.pages, axis)

    def update_config(self, config):
        print(config)
        header_lines = config.get('header_lines', self.header_lines)
        if header_lines is None:
            self.header_lines = self.LAST_HEADER_LINE + 1
        else:
            self.header_lines = header_lines
        self.DATA_START_COLUMN = config.get('data_start_column', 2)
        self.INITIAL_CHAPTER_NAME_COLUMN = config.get('initial_chapter_name_column', 1)
        self.data_to_fix = config.get('data_to_fix', self.data_to_fix)
        self.labels_to_fix = config.get('labels_to_fix', self.labels_to_fix)
        if isinstance(self.data_to_fix, list):
            self.data_to_fix = {(k[0], k[1]): v for k, v in self.data_to_fix}
        self.table_number = config.get('table_number', self.table_number)
        self.pages = config.get('pages', self.pages)
        self.filename = config.get('filename', self.filename)
            
    def read_singlepage_table(self, filename, page):
        self.update_config(self.config.get(str(page), {}))
        self.read_data(filename, page, self.table_number)
        self.convert_header_to_labels()
        self.merge_multilines_cells()
        self.remove_notes_from_chapter_names()
        self.delete_useless_columns()
        self.fix_data()
        self.convert_first_col_to_string()
        self.convert_data()

    def read_multipage_table(self, filename, pages, axis):
        data = None
        for page in pages:
            self.read_singlepage_table(filename, page)
            print('*-'*20)
            print(self.data)
            print('+-'*20)
            if data is None:
                data = self.data
                self.table_number = 0
            else:
                data = pd.concat([data, self.data], axis=axis,
                                 ignore_index=True)
        self.data = data

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
        for i, line in self.data.iterrows():
            if self.line_has_no_data(line):
                self.merge_with_previous_line(i)
                drop_list.append(line.name)
        self.data.drop(drop_list, inplace=True)        
        self.data.reset_index(drop=True, inplace=True)

    def line_has_no_data(self, line):
        a = line.iloc[self.DATA_START_COLUMN:].dropna()
        return a.empty
    
    def merge_with_previous_line(self, num):
        col = self.INITIAL_CHAPTER_NAME_COLUMN
        part1 = self.data.iloc[num - 1, col].strip()
        part2 = self.data.iloc[num, col].strip()
        self.data.iloc[num - 1, col] = part1 + " " + part2
        
    def remove_notes_from_chapter_names(self):
        col = self.INITIAL_CHAPTER_NAME_COLUMN
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

        dataset = self.data.iloc[:, self.DATA_START_COLUMN:]
        self.data.iloc[:,self.DATA_START_COLUMN:] = dataset.map(fun)
        self.data = self.data.convert_dtypes(convert_integer=False)

    def convert_first_col_to_string(self):
        self.data = self.data.astype({'Chapitre': str})

class BalanceGenerale(BaseView):
    DATA_START_COLUMN = 2
    INITIAL_CHAPTER_NAME_COLUMN = 1
    LAST_HEADER_LINE = 0

    def fix_labels(self, names):
        names[0] = "Chapitre"
        if not names[2]:
            names[2] = np.nan
        return names


class VueEnsembleDepenses(BaseView):
    DATA_START_COLUMN = 3
    INITIAL_CHAPTER_NAME_COLUMN = 1
    LAST_HEADER_LINE = 4

    def fix_labels(self, names):
        names[0] = 'Chapitre'
        names[1] = 'Titre Chapitre'
        names[2] = np.nan
        return names

    def fix_data(self):
        self.data.loc[0, 'Chapitre'] = 'Total'


class DetailParArticle(BaseView):
    DATA_START_COLUMN = 2
    INITIAL_CHAPTER_NAME_COLUMN = 1

if WRITE_REFERENCE_FILES:
    bgdi = BalanceGenerale('BP_2025_ville.pdf', 17, 1)
    bgdi.data.to_csv('bgdi.csv', float_format='%.2f', index=False)
    bgdf = BalanceGenerale('BP_2025_ville.pdf', 17, 2)
    bgdf.data.to_csv('bgdf.csv', float_format='%.2f', index=False)
    bgri = BalanceGenerale('BP_2025_ville.pdf', 19, 1)
    bgri.data.to_csv('bgri.csv', float_format='%.2f', index=False)
    bgrf = BalanceGenerale('BP_2025_ville.pdf', 19, 2)
    bgrf.data.to_csv('bgrf.csv', float_format='%.2f', index=False)
    vedi = VueEnsembleDepenses('BP_2025_ville.pdf', 21, 1)
    vedi.data.to_csv('vedi.csv', float_format='%.2f', index=False)
    veri = VueEnsembleDepenses('BP_2025_ville.pdf', 23, 1)
    veri.data.to_csv('veri.csv', float_format='%.2f', index=False)
    dadi1 = DetailParArticle('BP_2025_ville.pdf', 25, 1,
                            labels_to_fix={0: 'Chapitre',
                                           3: np.nan,
                                           4: 'Rar N-1 I'},
                            header_lines=5)
    dadi1.data.to_csv('dadi1.csv', float_format='%.2f', index=False)
    dadi2 = DetailParArticle('BP_2025_ville.pdf', 26, 0,
                            labels_to_fix={0: 'Chapitre'},
                            header_lines=5)
    dadi2.data.to_csv('dadi2.csv', float_format='%.2f', index=False)
    dadi = DetailParArticle('BP_2025_ville.pdf', [25, 26], 1,
                            labels_to_fix={0: 'Chapitre',
                                           3: np.nan,
                                           4: 'Rar N-1 I'},
                            header_lines=5)
    dadi.data.to_csv('dadi.csv', float_format='%.2f', index=False)
    dari = DetailParArticle('BP_2025_ville.pdf', [31, 32], 1,
                            header_lines=4,
                            labels_to_fix={0: 'Chapitre',
                                           1: 'Chap. / Art.',
                                           2: np.nan,
                                           },
                            data_to_fix = {(0, 'Chapitre'): 'Total'})
    #dari.data.to_csv('dari.csv', float_format='%.2f', index=False)

#print(dari.data)

with open('config.toml', 'rb') as f:
    conf = tomllib.load(f)
print(conf)
filename = conf['general']['filename']
for table in conf['general']['tables']:
    ct = conf[table]
    c = BaseView(filename, config=ct)
    print(c.data)
    if WRITE_REFERENCE_FILES:
        c.data.to_csv(table + '.csv', float_format='%.2f', index=False)

#dari = DetailParArticle('BP_2025_ville.pdf', [31, 32], 1,
#                        header_lines=4,
#                        labels_to_fix={0: 'Chapitre',
#                                       1: 'Chap. / Art.',
#                                       2: np.nan,
#                                       },
#                        data_to_fix = {(0, 'Chapitre'): 'Total'},
#                        config=conf)

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

    def _test_equals(self, act, ref, show=False):
        actual = self.convert_data(act)        
        reference = self.convert_data(ref)
        if show:
            print()
            print(actual)
            print(reference)
            print(actual.dtypes)
            print(reference.dtypes)
        return self.assertTrue(actual.equals(reference))
    
    def test_balance_generale_depenses_invest(self):
        act = BalanceGenerale('BP_2025_ville.pdf', 17, 1).data
        ref = pd.read_csv('bgdi-reference.csv')
        self._test_equals(act, ref)

    def test_balance_generale_depenses_fonct(self):
        act = BalanceGenerale('BP_2025_ville.pdf', 17, 2).data
        ref = pd.read_csv('bgdf-reference.csv')
        self._test_equals(act, ref)

    def test_balance_generale_recettes_invest(self):
        act = BalanceGenerale('BP_2025_ville.pdf', 19, 1).data
        ref = pd.read_csv('bgri-reference.csv')
        self._test_equals(act, ref)

    def test_balance_generale_recettes_fonct(self):
        act = BalanceGenerale('BP_2025_ville.pdf', 19, 2).data
        ref = pd.read_csv('bgrf-reference.csv')
        self._test_equals(act, ref)

    def test_vue_ensemble_depenses(self):
        act = VueEnsembleDepenses('BP_2025_ville.pdf', 21, 1).data
        ref = pd.read_csv('vedi-reference.csv')
        self._test_equals(act, ref)
        
    def test_vue_ensemble_recettes(self):
        act = VueEnsembleDepenses('BP_2025_ville.pdf', 23, 1).data
        ref = pd.read_csv('veri-reference.csv')
        self._test_equals(act, ref)

    def test_detail_par_article(self):
        act = DetailParArticle('BP_2025_ville.pdf', [25, 26],
                               1,
                               labels_to_fix={0: 'Chapitre',
                                              3: np.nan,
                                              4: 'Rar N-1 I'},
                               header_lines=5,
                               ).data
        ref = pd.read_csv('dadi-reference.csv')
        self._test_equals(act, ref, False)
        act = DetailParArticle(self.filename,
                               config=self.config['dari'],
                               ).data
        ref = pd.read_csv('dari-reference.csv')
        self._test_equals(act, ref, True)
       
        
if __name__ == '__main__':
    unittest.main()
