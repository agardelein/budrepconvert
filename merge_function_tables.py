#!/home/arnaud/venv/bin/python3

import os
import numpy as np
import pandas as pd

def convert_data(data, show=False):
    for i, v in enumerate(data.iloc[:,0]):
        if not isinstance(v, str) and \
           (isinstance(v, pd._libs.missing.NAType) or np.isnan(v)):
            data.iloc[i, 0] = ''
    return data.convert_dtypes(convert_integer=False)

def merge_dataframes(df1, df2):
    df = df1.copy(deep=True)
    for i, row in df2.iterrows():
        idx = row.name
        df.loc[idx, row.index] = row
    return df

expense = pd.DataFrame()
income = pd.DataFrame()
in_expense = False
for j in ['i', 'f']:
    for i in range(9):
        filename = f'f{i}{j}.csv'
        if not os.path.isfile(filename):
            continue
        df1 = convert_data(pd.read_csv(filename, index_col=0))
        income_start = df1.index.to_list().index('RECETTES')
        expense = merge_dataframes(expense, df1.iloc[1:income_start, :])
        income = merge_dataframes(income, df1.iloc[income_start + 1:, :])
    print(expense)
    print(expense.columns)
    print(expense.dtypes)
    print(income)
    print(income.columns)
    print(income.dtypes)
    expense.map(lambda x: np.nan if isinstance(x, bytes) and not x else x).to_csv(f'DEPENSES-{j}.csv', float_format='%.2f')
    income.map(lambda x: np.nan if isinstance(x, bytes) and not x else x).to_csv(f'RECETTES-{j}.csv', float_format='%.2f')
