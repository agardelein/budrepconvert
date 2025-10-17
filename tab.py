#!/home/arnaud/venv/bin/python3

import re
import locale
import tabula
import numpy as np
import pandas as pd

class BaseView:
    HEADER = []
    DROP_COLUMNS = []
    START_COLUMN = None
    def __init__(self, filename, page, rel_area=None):
        self.data = None
        self.read_data(filename, page, rel_area)
        self.data.drop(columns=self.DROP_COLUMNS, inplace=True)
        self.merge_nan_lines()
        self.extract_chapter_numbers()
        self.convert_data()
        #self.set_header()

    def read_data(self, filename, page, rel_area=None):
        str_area = [f"{i*100:.3f}" for i in rel_area]
        print(str_area)
        df = tabula.read_pdf(filename,
                             pages=page,
                             area=str_area,
                             relative_area=True,
                             pandas_options={'header': None},
                             )
        self.data = df[0]

    def merge_nan_lines(self):
        drop_list = []
        for i, line in self.data.iterrows():
            if self.is_nan_line(line):
                self.merge_with_previous_line(i)
                drop_list.append(line.name)
        self.data.drop(drop_list, inplace=True)

    def is_nan_line(self, line):
        a = line.iloc[self.START_COLUMN:].dropna()
        return a.empty

    def merge_with_previous_line(self, num):
        col = 1 if not self.DROP_COLUMNS else self.DROP_COLUMNS[0] - 1
        part1 = self.data.iloc[num - 1, col]
        part2 = self.data.iloc[num, col]
        part2 = part2.strip()
        self.data.iloc[num - 1, col] = part1 + " " + part2
        
    def extract_chapter_numbers(self):
        d = {0: ["" for x in range(len(self.data[0]))],
             1: ["" for x in range(len(self.data[0]))]}
        res = pd.DataFrame(d)
        found = False
        for i, s in enumerate(self.data[0]):
            m = re.match(r'(\d*\s{1})(.[^\(]*)(\(\d+\))*', str(s))
            if m is not None:
                found = True
                res.loc[i, 0] = m.groups()[0].strip()
                res.loc[i ,1] = m.groups()[1].strip()
        if found:
            self.data.drop(0, axis=1, inplace=True)
            self.data = pd.concat([res, self.data], axis=1)

    def convert_data(self):
        pass
    
    def set_header(self):
        names = dict(zip(list(self.data.columns), self.HEADER))
        self.data.rename(columns=names, inplace=True)

class BaseBalanceGenerale(BaseView):
    START_COLUMN = 2
        
class BalanceGeneraleInvest(BaseBalanceGenerale):
    HEADER = ['Chapitre', 'Investissement', 'Opérations Réelles', 'Opérations d\'ordre', 'Total']
    DROP_COLUMNS = [2]

class BalanceGeneraleFonct(BaseBalanceGenerale):
    HEADER = ['Chapitre', 'Fonctionnement', 'Opérations Réelles', 'Opérations d\'ordre', 'Total']

class BaseVueEnsemble(BaseView):
    START_COLUMN = 3
    
class VueEnsembleDepensesInvest(BaseVueEnsemble):
    HEADER = ['Chapitre',
              'Intitulé Chapitre',
              'Pour mémoire budget précédent',
              'RAR N-1',
              'Vote de l\'assemblée sur les AP lors de la séance budgétaire',
              'Proposition nouvelles',
              'Vote de l\'assemblée',
              'Pour information, dépenses gérées dans le cadre d\'une AP',
              'Pour information, dépenses gérées hors AP',
              'Total (RAR N-1 + Vote)',
              ]
    DROP_COLUMNS = [1]
    
area = [35/280, 13/197, 132/280, 183/197]
bgdi = BalanceGeneraleInvest('BP_2025_ville.pdf',
                              17,
                              rel_area=area)

area = [165/280, 13/197, 220/280, 183/197]
bgdf = BalanceGeneraleFonct('BP_2025_ville.pdf',
                              17,
                              rel_area=area)

area = [35/280, 13/197, 132/280, 183/197]
bgri = BalanceGeneraleInvest('BP_2025_ville.pdf',
                              19,
                              rel_area=area)
area = [179/280, 13/197, 245/280, 183/197]
bgrf = BalanceGeneraleFonct('BP_2025_ville.pdf',
                              19,
                              rel_area=area)

area = [56/210, 16/297, 155/210, 282/297]
vedi = VueEnsembleDepensesInvest('BP_2025_ville.pdf',
                                 21,
                                 rel_area=area)
print(bgdi.data)
print(bgdf.data)
print(bgri.data)
print(bgrf.data)
print(vedi.data)
