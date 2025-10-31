#!/home/arnaud/venv/bin/python3

import re
import locale
import tabula
import numpy as np
import pandas as pd
import unittest

WRITE_FILES = False

class BaseView:
    DATA_START_COLUMN = None
    INITIAL_CHAPTER_NAME_COLUMN = None
    LAST_HEADER_LINE = None

    def __init__(self, filename, page, table_number):
        self.data = None
        self.read_data(filename, page, table_number)
        self.convert_header_to_labels()
        self.merge_nan_lines()
        self.remove_notes_from_chapter_names()
        self.delete_useless_columns()
        self.specific_process_data()
        self.convert_data()

    def read_data(self, filename, page, table_number):
        df = tabula.read_pdf(filename,
                             pages=page,
                             stream=True,
                             pandas_options={'header': None},
                             )
        self.data = df[table_number]

    def convert_header_to_labels(self):
        drop_list = list(range(self.LAST_HEADER_LINE + 1))
        names = {}
        for i, col in self.data.items():
            s = ' '.join(self.merge_header_cells(col)).title()
            names[i] = self.remove_notes(s)
        names = self.fix_labels(names)
        self.data.rename(columns=names, inplace=True)
        self.data.drop(drop_list, inplace=True)
        self.data.reset_index(drop=True, inplace=True)

    def fix_labels(self):
        raise NotImplementedError

    def merge_header_cells(self, cells):
        return cells[:self.LAST_HEADER_LINE+ 1].dropna().astype(str)
    
    def merge_nan_lines(self):
        drop_list = []
        for i, line in self.data.iterrows():
            if self.is_nan_line(line):
                self.merge_with_previous_line(i)
                drop_list.append(line.name)
        self.data.drop(drop_list, inplace=True)        
        self.data.reset_index(drop=True, inplace=True)

    def is_nan_line(self, line):
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

    def process_data(self):
        raise NotImplementedError

    def specific_process_data(self):
        pass
    
    def convert_data(self):
        def fun(s):
            if not isinstance(s, str):
                return s
            else:
                rep = s.replace(' ', '').replace(',', '.')
                try:
                    return float(rep)
                except ValueError:
                    return s

        dataset = self.data.iloc[:, self.DATA_START_COLUMN:]
        self.data.iloc[:,self.DATA_START_COLUMN:] = dataset.map(fun)
        self.data = self.data.convert_dtypes(convert_integer=False)

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
    DROP_COLUMNS = [1]

    def fix_labels(self, names):
        names[0] = 'Chapitre'
        names[1] = 'Titre Chapitre'
        names[2] = np.nan
        return names

    def specific_process_data(self):
        self.data.loc[0, 'Chapitre'] = 'Total'

    def extract_chapter_numbers(self):
        nums= pd.Series([np.nan for x in range(self.data[0].size)])
        names = pd.Series(["" for x in range(self.data[0].size)])
        for i, s in enumerate(self.data[0]):
            s = self.remove_notes(s)
            nums[i] = self.find_chapter_number(s)
            s = self.remove_chapter_number(s)
            names[i] = self.find_chapter_name(s)
        self.data.drop(0, axis=1, inplace=True)
        self.data = pd.concat([nums, names, self.data], axis=1)

    def find_chapter_number(self, s):
        if not isinstance(s, str):
            return s
        m = re.match(r'^(\d+)', s)
        if m is None:
            return np.nan
        return int(m.groups()[0])

    def find_chapter_name(self, s):
        if not isinstance(s, str):
            return s
        return s.strip()

    def remove_chapter_number(self, s):
        if not isinstance(s, str):
            return s
        return re.sub(r'^(\d+)', '', s)

class DetailParArticle(BaseView):
    DATA_START_COLUMN = 2
    INITIAL_CHAPTER_NAME_COLUMN = 1
    LAST_HEADER_LINE = 4

    def fix_labels(self, names):
        names[0] = 'Chapitre'
        return names

if WRITE_FILES:
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
    dadi1 = DetailParArticle('BP_2025_ville.pdf', 25, 1)
    dadi1.data.to_csv('dadi1.csv', float_format='%.2f', index=False)
    dadi2 = DetailParArticle('BP_2025_ville.pdf', 26, 0)
    dadi2.data.to_csv('dadi2.csv', float_format='%.2f', index=False)


print('-'*50, 'Done')

class test_bg(unittest.TestCase):

    def convert_data(self, data):
        return data.convert_dtypes(convert_integer=False)

    def _test_equals(self, act, ref, show=False):
        actual = self.convert_data(act)        
        reference = self.convert_data(ref)
        if show:
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
        act = DetailParArticle('BP_2025_ville.pdf', 25, 1).data
        ref = pd.read_csv('dadi1-reference.csv')
        self._test_equals(act, ref)
        act = DetailParArticle('BP_2025_ville.pdf', 26, 0).data
        ref = pd.read_csv('dadi2-reference.csv')
        self._test_equals(act, ref)
        
if __name__ == '__main__':
    unittest.main()
