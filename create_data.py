import pandas as pd
import numpy as np
num_records=500
pct_pla=0.5
pct_tpu=0.1
pct_petg=0.02
pct_other=1-(pct_pla+pct_petg+pct_tpu)

total_weight=np.random.uniform(0,285,size=num_records)
data={
    'Date':pd.date_range('2025-01-01',periods=num_records,freq='D'),
    'PLA_weight':total_weight*pct_pla,
    'TPU_weight':total_weight*pct_tpu,
    'PETG_weight':total_weight*pct_petg,
    'Mixed_weight':total_weight*pct_other,
    'num_students':np.random.randint(0,50,size=num_records)
}

df=pd.DataFrame(data)
print(f"% by weight of PLA: {df['PLA_weight'].sum()/total_weight.sum()}")
print(f"% by weight of TPU: {df['TPU_weight'].sum()/total_weight.sum()}")
print(f"% by weight of PVA: {df['PETG_weight'].sum()/total_weight.sum()}")
print(f"% by weight of mixed: {df['Mixed_weight'].sum()/total_weight.sum()}")
df.to_csv('data_500_days.csv',index=False)


