# -*- coding: utf-8 -*-
"""Standard implicit-feedback top-N baselines on bench_foodcom (numpy/scipy, CPU).
Baselines: Popularity, ItemKNN (cosine), BPR-MF. Metrics: Recall@10/20, NDCG@10, HR@10."""
import numpy as np, scipy.sparse as sp, time, json, os
np.random.seed(0)
D="/tmp/bench/synth50"

def load(path):
    d={}
    for line in open(os.path.join(D,path)):
        p=line.split()
        if not p: continue
        d[int(p[0])]=[int(x) for x in p[1:]]
    return d
train=load("train.txt"); test=load("test.txt")
n_users=max(max(train), max(test))+1
n_items=max(max(max(v) for v in train.values()), max(max(v) for v in test.values()))+1
print(f"users {n_users} items {n_items}")

rows=[u for u in train for _ in train[u]]
cols=[i for u in train for i in train[u]]
R=sp.csr_matrix((np.ones(len(rows)),(rows,cols)),shape=(n_users,n_items))
test_users=sorted(test)
K1,K2=10,20

def evaluate(score_fn, name, batch=256):
    t=time.time()
    rec10=rec20=ndcg10=hr10=0.0; n=0
    idcg10=np.array([1/np.log2(i+2) for i in range(K1)]).cumsum()
    for s in range(0,len(test_users),batch):
        us=test_users[s:s+batch]
        S=score_fn(us)                      # (b, n_items) dense scores
        for bi,u in enumerate(us):
            sc=S[bi].copy()
            sc[train[u]]=-1e9               # mask seen
            top=np.argpartition(-sc,K2)[:K2]
            top=top[np.argsort(-sc[top])]   # sorted top-K2
            gt=set(test[u])
            hits20=[1 if it in gt else 0 for it in top]
            hits10=hits20[:K1]
            nh=sum(hits10)
            rec10+=nh/min(len(gt),K1)
            rec20+=sum(hits20)/min(len(gt),K2)
            hr10+=1.0 if nh>0 else 0.0
            dcg=sum(h/np.log2(r+2) for r,h in enumerate(hits10))
            ndcg10+=dcg/idcg10[min(len(gt),K1)-1]
            n+=1
    print(f"{name:10s} Recall@10={rec10/n:.4f} Recall@20={rec20/n:.4f} NDCG@10={ndcg10/n:.4f} HR@10={hr10/n:.4f}  ({time.time()-t:.0f}s)")
    return {"model":name,"Recall@10":round(rec10/n,4),"Recall@20":round(rec20/n,4),"NDCG@10":round(ndcg10/n,4),"HR@10":round(hr10/n,4)}

results=[]
# --- Popularity ---
pop=np.asarray(R.sum(0)).ravel()
results.append(evaluate(lambda us: np.tile(pop,(len(us),1)), "Popularity"))

# --- ItemKNN (cosine) ---
col_norm=np.sqrt(np.asarray(R.multiply(R).sum(0)).ravel())+1e-9
Rc=(R @ sp.diags(1.0/col_norm)).tocsr()     # column-normalized (cosine)
Sim=(Rc.T @ Rc).tocsr()                      # item-item cosine similarity (sparse)
Sim.setdiag(0); Sim.eliminate_zeros()
print(f"ItemKNN sim nnz={Sim.nnz:,}")
def knn_score(us):
    return np.asarray((R[us] @ Sim).todense())   # user-history * item-item cosine
results.append(evaluate(knn_score, "ItemKNN"))

# --- BPR-MF (numpy) ---
dim=64; lr=0.05; reg=0.002; epochs=25
U=(np.random.randn(n_users,dim)*0.01); V=(np.random.randn(n_items,dim)*0.01)
pos_pairs=np.array([(u,i) for u in train for i in train[u]])
allitems=np.arange(n_items)
train_sets={u:set(v) for u,v in train.items()}
t0=time.time()
for ep in range(epochs):
    np.random.shuffle(pos_pairs)
    for s in range(0,len(pos_pairs),4096):
        b=pos_pairs[s:s+4096]; uu=b[:,0]; ii=b[:,1]
        jj=np.random.randint(0,n_items,size=len(b))
        xui=np.einsum('bd,bd->b',U[uu],V[ii]); xuj=np.einsum('bd,bd->b',U[uu],V[jj])
        d=1/(1+np.exp(xui-xuj))             # sigmoid(-(xui-xuj))
        gu=(V[ii]-V[jj])*d[:,None]-reg*U[uu]
        gi= U[uu]*d[:,None]-reg*V[ii]
        gj=-U[uu]*d[:,None]-reg*V[jj]
        np.add.at(U,uu,lr*gu); np.add.at(V,ii,lr*gi); np.add.at(V,jj,lr*gj)
print(f"BPR trained {epochs} epochs ({time.time()-t0:.0f}s)")
results.append(evaluate(lambda us: U[us] @ V.T, "BPR-MF"))

json.dump({"dataset":"bench_foodcom","n_users":n_users,"n_items":n_items,
           "n_train_int":int(R.nnz),"metrics":results,
           "note":"Standard implicit top-N, leave-last-20%-out per user, all-item ranking, seen-item masking."},
          open(os.path.join(D,"baseline_results.json"),"w"), indent=2)
print("saved baseline_results.json")
