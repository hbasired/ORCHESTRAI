#!/usr/bin/env python3
"""Generate the brain-STRENGTHENING notebook: XGBoost on AI4I 2020 (gaps G-034 + G-033 recall-tune).

Same clean, leakage-free AI4I tabular setup as Stage 4, but swaps the MLP for XGBoost (usually stronger on
tabular) and reports TWO thresholds: F1-optimal AND a recall-tuned one (catch more failures). Exports
`pdm_xgb_brain.zip`.

Run: python scripts/build_stage04b_xgboost_notebook.py
Out: notebooks/stage04b_xgboost_pdm_colab.ipynb
"""
import json, os
def md(*l): return {"cell_type":"markdown","metadata":{},"source":_s(l)}
def code(*l): return {"cell_type":"code","metadata":{},"execution_count":None,"outputs":[],"source":_s(l)}
def _s(lines):
    t="\n".join(lines); p=t.split("\n"); return [x+("\n" if i<len(p)-1 else "") for i,x in enumerate(p)]

cells=[]
cells.append(md(
    "# Stage 4b — STRONGER PdM brain (XGBoost on AI4I 2020)",
    "",
    "Upgrades the Stage-4 MLP (PR-AUC 0.679, recall 0.61) using **XGBoost** — usually stronger on tabular data —",
    "and reports a **recall-tuned threshold** so we catch more failures (gaps G-034 + G-033). Same clean,",
    "**leakage-free** AI4I setup (leaky `TWF/HDF/PWF/OSF/RNF` dropped, stratified split). `Runtime ▸ Run all` →",
    "downloads `pdm_xgb_brain.zip` — send it back. No GPU needed; no API key.",
))
cells.append(code(
    "import numpy as np, pandas as pd, requests, zipfile, io, json, pickle, os",
    "try:",
    "    import xgboost as xgb",
    "except Exception:",
    "    import subprocess, sys; subprocess.run([sys.executable,'-m','pip','install','-q','xgboost']); import xgboost as xgb",
    "from sklearn.model_selection import train_test_split",
    "from sklearn.preprocessing import StandardScaler",
    "from sklearn.metrics import roc_auc_score, average_precision_score, classification_report, precision_recall_curve, confusion_matrix",
    "SEED=42; np.random.seed(SEED)",
    "print('xgboost', xgb.__version__)",
))
cells.append(code(
    "url='https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip'",
    "raw=pd.read_csv(zipfile.ZipFile(io.BytesIO(requests.get(url).content)).open('ai4i2020.csv'))",
    "df=raw.copy()",
    "df['Type_ord']=df['Type'].map({'L':0,'M':1,'H':2}).astype('float32')",
    "df['temp_diff']=df['Process temperature [K]']-df['Air temperature [K]']",
    "df['power_w']=df['Torque [Nm]']*df['Rotational speed [rpm]']*2*np.pi/60.0",
    "FEATURES=['Type_ord','Air temperature [K]','Process temperature [K]','Rotational speed [rpm]','Torque [Nm]','Tool wear [min]','temp_diff','power_w']",
    "X=df[FEATURES].values.astype('float32'); y=df['Machine failure'].values.astype('int')",
    "print('pos rate', round(float(y.mean()),4), '(real ~3.4%) | dropped leaky TWF/HDF/PWF/OSF/RNF')",
))
cells.append(code(
    "Xtr,Xtmp,ytr,ytmp=train_test_split(X,y,test_size=0.30,stratify=y,random_state=SEED)",
    "Xva,Xte,yva,yte=train_test_split(Xtmp,ytmp,test_size=0.50,stratify=ytmp,random_state=SEED)",
    "scaler=StandardScaler().fit(Xtr)  # XGBoost doesn't need it, but we keep one for a uniform inference path",
    "spw=float((ytr==0).sum()/max((ytr==1).sum(),1))",
    "clf=xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.9,",
    "    colsample_bytree=0.9, scale_pos_weight=spw, eval_metric='aucpr', early_stopping_rounds=30, random_state=SEED)",
    "clf.fit(Xtr,ytr, eval_set=[(Xva,yva)], verbose=False)",
    "print('best_iteration', clf.best_iteration)",
))
cells.append(code(
    "pte=clf.predict_proba(Xte)[:,1]; pva=clf.predict_proba(Xva)[:,1]",
    "roc=roc_auc_score(yte,pte); prauc=average_precision_score(yte,pte)",
    "prec,rec,thr=precision_recall_curve(yva,pva); f1=2*prec*rec/(prec+rec+1e-9)",
    "THR_F1=float(thr[max(0,f1[:-1].argmax())])",
    "# recall-tuned: lowest threshold giving val recall >= 0.80 (G-033)",
    "rec_ok=np.where(rec[:-1]>=0.80)[0]; THR_RECALL=float(thr[rec_ok[-1]]) if len(rec_ok) else THR_F1",
    "print(f'TEST ROC-AUC {roc:.3f} | PR-AUC {prauc:.3f} | baseline {yte.mean():.3f}')",
    "for name,T in [('F1-opt',THR_F1),('recall>=0.80',THR_RECALL)]:",
    "    pr=(pte>=T).astype(int); cm=confusion_matrix(yte,pr)",
    "    print(f'\\n[{name}] thr={T:.3f}  confusion [[TN,FP],[FN,TP]]={cm.tolist()}')",
    "    print(classification_report(yte,pr,digits=3))",
))
cells.append(code(
    "os.makedirs('brain',exist_ok=True)",
    "clf.save_model('brain/pdm_failure_predictor_xgb.json')",
    "pickle.dump(scaler,open('brain/scaler.pkl','wb'))",
    "meta={'arch':'XGBoost','features':FEATURES,'type_encoding':{'L':0,'M':1,'H':2},",
    "      'threshold_f1':round(THR_F1,4),'threshold_recall80':round(THR_RECALL,4),'task':'per-snapshot failure-risk (tabular)','seed':SEED,",
    "      'scaler_mean':scaler.mean_.tolist(),'scaler_scale':scaler.scale_.tolist()}",
    "json.dump(meta,open('brain/model_meta.json','w'),indent=2)",
    "metrics={'roc_auc':round(float(roc),4),'pr_auc':round(float(prauc),4),'threshold_f1':round(THR_F1,4),",
    "         'threshold_recall80':round(THR_RECALL,4),'test_positive_rate':round(float(yte.mean()),4),",
    "         'n_test':int(len(yte)),'dataset':'AI4I 2020 (XGBoost, clean stratified split, no leakage)','model':'xgboost'}",
    "json.dump(metrics,open('brain/metrics.json','w'),indent=2)",
    "with zipfile.ZipFile('pdm_xgb_brain.zip','w',zipfile.ZIP_DEFLATED) as z:",
    "    for fn in ['pdm_failure_predictor_xgb.json','scaler.pkl','model_meta.json','metrics.json']: z.write('brain/'+fn,fn)",
    "print(json.dumps(metrics,indent=2))",
    "try:",
    "    from google.colab import files; files.download('pdm_xgb_brain.zip')",
    "except Exception as e: print('grab pdm_xgb_brain.zip from the file browser', e)",
))
cells.append(md(
    "---",
    "**Compare vs the MLP (Stage 4):** MLP was ROC-AUC 0.972 / PR-AUC 0.679 / recall 0.61. If XGBoost's PR-AUC is",
    "higher and the recall-tuned threshold lifts recall toward 0.8 with acceptable precision, send `pdm_xgb_brain.zip`",
    "and I'll wire it as the stronger brain (and pick the recall-tuned threshold for maintenance).",
))
nb={"cells":cells,"metadata":{"kernelspec":{"display_name":"Python 3","name":"python3"},"language_info":{"name":"python"},"colab":{"provenance":[]}},"nbformat":4,"nbformat_minor":5}
os.makedirs("notebooks",exist_ok=True)
json.dump(nb,open("notebooks/stage04b_xgboost_pdm_colab.ipynb","w",encoding="utf-8"),indent=1)
print("wrote notebooks/stage04b_xgboost_pdm_colab.ipynb",len(cells),"cells")
