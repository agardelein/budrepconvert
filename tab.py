#!/home/arnaud/venv/bin/python3

import re
import locale
import tabula
import numpy as np
import pandas as pd

class BaseView:
    DATA_START_COLUMN = None
    INITIAL_CHAPTER_NAME_COLUMN = None

    def __init__(self, filename, page, table_number):
        self.data = None
        self.read_data(filename, page, table_number)
        self.process_header()
        self.merge_nan_lines()
        self.remove_notes_from_chapter_names()
        self.specific_process_data()
        self.convert_data()

    def read_data(self, filename, page, table_number):
        df = tabula.read_pdf(filename,
                             pages=page,
                             stream=True,
                             pandas_options={'header': None},
                             )
        self.data = df[table_number]

    def process_header(self):
        raise NotImplementedError
        
    def merge_nan_lines(self):
        drop_list = []
        for i, line in self.data.iterrows():
            if self.is_nan_line(line):
                self.merge_with_previous_line(i)
                drop_list.append(line.name)
        self.data.drop(drop_list, inplace=True)        

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

    def process_data(self):
        raise NotImplementedError
    
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

    def set_header(self):
        names = dict(zip(list(self.data.columns), self.HEADER))
        self.data.rename(columns=names, inplace=True)

class BaseBalanceGenerale(BaseView):
    DATA_START_COLUMN = 2
    INITIAL_CHAPTER_NAME_COLUMN = 1

    def process_header(self):
        header = self.data.iloc[0, :]
        names = {}
        for i, h in enumerate(header):
            if isinstance(h, str):
                names[i] = self.remove_notes(h).title()
            else:
                names[i] = h
        names[0] = "Chapitre"
        self.data.rename(columns=names, inplace=True)
        self.data.drop(0, inplace=True)
        self.data.reset_index(drop=True, inplace=True)


class BalanceGeneraleInvest(BaseBalanceGenerale):
    TABLE_NUMBER = 1

    def specific_process_data(self):
        self.data.drop(columns=[np.nan], inplace=True)


class BalanceGeneraleFonct(BaseBalanceGenerale):
    TABLE_NUMBER = 2

    def specific_process_data(self):
        pass


class BaseVueEnsemble(BaseView):
    DATA_START_COLUMN = 3
    INITIAL_CHAPTER_NAME_COLUMN = 1
    LAST_HEADER_LINE = 4
    DROP_COLUMNS = [1]
    TABLE_NUMBER = 1

    def process_header(self):
        names = {}
        for i, col in self.data.items():
            s = ' '.join(self.merge_header_cells(col)).title()
            names[i] = self.remove_notes(s)
        names[0] = 'Chapitre'
        names[1] = 'Titre Chapitre'
        names[2] = np.nan
        self.data.rename(columns=names, inplace=True)
        self.data.drop(list(range(self.LAST_HEADER_LINE + 1)),
                       inplace=True)
        self.data.reset_index(drop=True, inplace=True)

    def merge_header_cells(self, cells):
        return cells[:self.LAST_HEADER_LINE+ 1 ].dropna()
    
    def specific_process_data(self):
        self.data.drop(columns=[np.nan], inplace=True)
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
    
class VueEnsembleDepensesInvest(BaseVueEnsemble):
    pass
    
bgdi = BalanceGeneraleInvest('BP_2025_ville.pdf', 17, 1)

bgdf = BalanceGeneraleFonct('BP_2025_ville.pdf', 17, 2)

bgri = BalanceGeneraleInvest('BP_2025_ville.pdf', 19, 1)

bgrf = BalanceGeneraleFonct('BP_2025_ville.pdf', 19, 2)

vedi = VueEnsembleDepensesInvest('BP_2025_ville.pdf', 21, 1)

veri = VueEnsembleDepensesInvest('BP_2025_ville.pdf', 23, 1)

print('-'*50, 'Done')
print(bgdi.data)
print(bgdf.data)
print(bgri.data)
print(bgrf.data)
print(vedi.data)
print(veri.data)
