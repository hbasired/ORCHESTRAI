#!/usr/bin/env python3
"""Generate the Stage-5 demand-forecasting notebook: LSTM on UCI Bike Sharing (#275), leakage-free.

Time-series done RIGHT (the lesson from the failed AI4I-windowed run): CHRONOLOGICAL split (train=earliest,
test=latest), windows built within each segment (no cross-split leakage), `casual`/`registered` dropped (they
sum to the target `cnt`). Honest baselines (persistence + seasonal-naive). Exports `demand_brain.zip`.

Run: python scripts/build_stage05_demand_notebook.py
Out: notebooks/stage05_demand_forecasting_colab.ipynb
"""
import json, os
def md(*l): return {"cell_type":"markdown","metadata":{},"source":_s(l)}
def code(*l): return {"cell_type":"code","metadata":{},"execution_count":None,"outputs":[],"source":_s(l)}
def _s(lines):
    t="\n".join(lines); p=t.split("\n"); return [x+("\n" if i<len(p)-1 else "") for i,x in enumerate(p)]

cells=[]
cells.append(md(
    "# Stage 5 — Demand Forecasting brain (LSTM, UCI Bike Sharing)",
    "",
    "Forecasts next-hour demand from a 24-hour window. **Leakage-free time series:** chronological split",
    "(train = earliest, test = latest), windows built *within* each segment, `casual`/`registered` dropped (they",
    "sum to the target `cnt`). Honest baselines: **persistence** (next = last) and **seasonal-naive** (next = 24h ago).",
    "",
    "`Runtime ▸ GPU ▸ Run all` → downloads `demand_brain.zip` — send it back. No API key.",
    "Proxy dataset (bike demand) for the supply-chain head; re-fit on real order data before pilot.",
))
cells.append(code(
    "import numpy as np, pandas as pd, requests, zipfile, io, json, pickle, os, torch",
    "import torch.nn as nn; from torch.utils.data import TensorDataset, DataLoader",
    "from sklearn.preprocessing import StandardScaler",
    "import matplotlib.pyplot as plt",
    "DEVICE='cuda' if torch.cuda.is_available() else 'cpu'; print('device',DEVICE)",
    "SEED=42; np.random.seed(SEED); torch.manual_seed(SEED)",
))
cells.append(code(
    "url='https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip'",
    "z=zipfile.ZipFile(io.BytesIO(requests.get(url).content))",
    "df=pd.read_csv(z.open('hour.csv')).sort_values('instant').reset_index(drop=True)",
    "print(df.shape, '| columns:', df.columns.tolist())",
    "# Drop casual+registered (cnt = casual+registered -> target leakage). Keep cnt + covariates.",
    "FEATURES=['cnt','temp','atemp','hum','windspeed','hr','weekday','workingday','holiday','weathersit','season']",
    "WINDOW=24; data=df[FEATURES].values.astype('float32')",
    "print('rows', len(data), '| features', FEATURES)",
))
cells.append(code(
    "n=len(data); tr_end=int(0.70*n); va_end=int(0.85*n)  # CHRONOLOGICAL split (no shuffle)",
    "scaler=StandardScaler().fit(data[:tr_end])  # fit on TRAIN only",
    "cnt_mean,cnt_std=float(scaler.mean_[0]),float(scaler.scale_[0])  # cnt is column 0",
    "sc=scaler.transform(data).astype('float32')",
    "def windows(lo,hi):",
    "    X,y,yraw,persist,season=[],[],[],[],[]",
    "    for end in range(lo+WINDOW, hi):",
    "        X.append(sc[end-WINDOW:end]); y.append(sc[end,0]); yraw.append(data[end,0])",
    "        persist.append(data[end-1,0]); season.append(data[end-24,0] if end-24>=0 else data[end-1,0])",
    "    return (np.array(X,'float32'),np.array(y,'float32'),np.array(yraw,'float32'),",
    "            np.array(persist,'float32'),np.array(season,'float32'))",
    "Xtr,ytr,_,_,_=windows(0,tr_end); Xva,yva,_,_,_=windows(tr_end,va_end)",
    "Xte,yte,yte_raw,persist_te,season_te=windows(va_end,n)",
    "print('train/val/test windows', Xtr.shape, Xva.shape, Xte.shape)",
))
cells.append(code(
    "class DemandLSTM(nn.Module):",
    "    def __init__(self,d,hidden=64,layers=2,dropout=0.2):",
    "        super().__init__()",
    "        self.lstm=nn.LSTM(d,hidden,num_layers=layers,batch_first=True,dropout=dropout if layers>1 else 0.0)",
    "        self.head=nn.Linear(hidden,1)",
    "    def forward(self,x):",
    "        h,_=self.lstm(x); return self.head(h[:,-1,:]).squeeze(-1)",
    "CFG=dict(arch='LSTM',input_dim=len(FEATURES),hidden=64,layers=2,dropout=0.2,window=WINDOW,",
    "         features=FEATURES,cnt_mean=cnt_mean,cnt_std=cnt_std)",
    "model=DemandLSTM(CFG['input_dim'],CFG['hidden'],CFG['layers'],CFG['dropout']).to(DEVICE); print(model)",
))
cells.append(code(
    "def dl(Xa,ya,bs=128,sh=False): return DataLoader(TensorDataset(torch.tensor(Xa),torch.tensor(ya)),batch_size=bs,shuffle=sh)",
    "tr,va=dl(Xtr,ytr,sh=True),dl(Xva,yva)",
    "crit=nn.L1Loss(); opt=torch.optim.Adam(model.parameters(),lr=1e-3,weight_decay=1e-5)",
    "def val_mae():",
    "    model.eval(); P=[];T=[]",
    "    with torch.no_grad():",
    "        for xb,yb in va: P.append(model(xb.to(DEVICE)).cpu().numpy()); T.append(yb.numpy())",
    "    p=np.concatenate(P)*cnt_std+cnt_mean; t=np.concatenate(T)*cnt_std+cnt_mean",
    "    return float(np.mean(np.abs(p-t)))",
    "best,bs,bad=1e9,None,0",
    "for ep in range(80):",
    "    model.train()",
    "    for xb,yb in tr: opt.zero_grad(); loss=crit(model(xb.to(DEVICE)),yb.to(DEVICE)); loss.backward(); opt.step()",
    "    m=val_mae()",
    "    if m<best: best,bs,bad=m,{k:v.cpu().clone() for k,v in model.state_dict().items()},0",
    "    else:",
    "        bad+=1",
    "        if bad>=8: print('early stop @',ep); break",
    "model.load_state_dict(bs); print('best val MAE (rides):', round(best,2))",
))
cells.append(code(
    "model.eval()",
    "with torch.no_grad(): pte=model(torch.tensor(Xte).to(DEVICE)).cpu().numpy()*cnt_std+cnt_mean",
    "def mae(a,b): return float(np.mean(np.abs(a-b)))",
    "def rmse(a,b): return float(np.sqrt(np.mean((a-b)**2)))",
    "def mape(a,b): m=b>1; return float(np.mean(np.abs((a[m]-b[m])/b[m]))*100)",
    "M={'model':{'MAE':mae(pte,yte_raw),'RMSE':rmse(pte,yte_raw),'MAPE':mape(pte,yte_raw)},",
    "   'persistence':{'MAE':mae(persist_te,yte_raw),'RMSE':rmse(persist_te,yte_raw)},",
    "   'seasonal_naive_24h':{'MAE':mae(season_te,yte_raw),'RMSE':rmse(season_te,yte_raw)}}",
    "imp=100*(M['persistence']['MAE']-M['model']['MAE'])/M['persistence']['MAE']",
    "print(json.dumps(M,indent=2)); print(f'improvement over persistence (MAE): {imp:.1f}%')",
    "plt.figure(figsize=(12,4)); plt.plot(yte_raw[:300],label='actual'); plt.plot(pte[:300],label='LSTM'); plt.plot(persist_te[:300],label='persistence',alpha=.4); plt.legend(); plt.title('test forecast (first 300 h)'); plt.show()",
))
cells.append(code(
    "os.makedirs('brain',exist_ok=True)",
    "torch.save(model.state_dict(),'brain/demand_forecaster.pt')",
    "pickle.dump(scaler,open('brain/scaler.pkl','wb'))",
    "meta={**CFG,'scaler_mean':scaler.mean_.tolist(),'scaler_scale':scaler.scale_.tolist()}",
    "json.dump(meta,open('brain/model_meta.json','w'),indent=2)",
    "metrics={'mae':round(M['model']['MAE'],3),'rmse':round(M['model']['RMSE'],3),'mape':round(M['model']['MAPE'],3),",
    "         'persistence_mae':round(M['persistence']['MAE'],3),'seasonal_naive_mae':round(M['seasonal_naive_24h']['MAE'],3),",
    "         'improvement_over_persistence_pct':round(imp,2),'dataset':'UCI Bike Sharing #275 (chronological split, no leakage)','window':WINDOW}",
    "json.dump(metrics,open('brain/metrics.json','w'),indent=2)",
    "with zipfile.ZipFile('demand_brain.zip','w',zipfile.ZIP_DEFLATED) as zz:",
    "    for fn in ['demand_forecaster.pt','scaler.pkl','model_meta.json','metrics.json']: zz.write('brain/'+fn,fn)",
    "print('saved demand_brain.zip')",
    "try:",
    "    from google.colab import files; files.download('demand_brain.zip')",
    "except Exception as e: print('grab demand_brain.zip from the file browser', e)",
))
cells.append(md(
    "---",
    "**Sanity:** the LSTM MAE must beat **persistence** (and ideally seasonal-naive) on the *latest* (test) period",
    "— if it doesn't beat persistence, the model has no real value; tell me and I'll adjust before wiring.",
))
nb={"cells":cells,"metadata":{"kernelspec":{"display_name":"Python 3","name":"python3"},"language_info":{"name":"python"},"accelerator":"GPU","colab":{"provenance":[]}},"nbformat":4,"nbformat_minor":5}
os.makedirs("notebooks",exist_ok=True)
json.dump(nb,open("notebooks/stage05_demand_forecasting_colab.ipynb","w",encoding="utf-8"),indent=1)
print("wrote notebooks/stage05_demand_forecasting_colab.ipynb",len(cells),"cells")
