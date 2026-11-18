"""Build allowlisted public labels from private proposal export; no prose output."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from cultural_labels_contract import COLUMNS, FACETS, validate_frame
def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); args=ap.parse_args()
    core=pd.read_parquet(args.root/'data/corpus/recipes_structured.parquet',columns=['recipe_id'])
    names={'Cuisine':'Cuisine_declared_v1','Region':'Region_declared_v1',**{f:f+'_declared_v2' for f in FACETS if f not in ['Cuisine','Region']}}
    fields=['recipe_id','label_enrichment_status','label_enrichment_provenance_json']+['proposed_'+v for v in names.values()]
    source=pd.read_parquet(args.input,columns=fields)
    source=source[source.recipe_id.isin(core.recipe_id)&source.label_enrichment_status.isin(['proposal_pending_review','abstained'])]
    frame=pd.DataFrame({'recipe_id':source.recipe_id,'status':source.label_enrichment_status.map({'proposal_pending_review':'proposed','abstained':'abstain'}),
                        'review_status':'pending','taxonomy':'cultural_facets_v2_20261117',
                        'partial_response':source.label_enrichment_provenance_json.map(lambda x:bool((json.loads(x).get('recovery') or {}).get('partial_response')))})
    for facet,suffix in names.items(): frame['proposed_'+facet+'_json']=source['proposed_'+suffix]
    frame=frame[COLUMNS].sort_values('recipe_id').reset_index(drop=True)
    problems=validate_frame(frame,core.recipe_id)
    if problems: raise ValueError(problems)
    folder=args.root/'data/cultural_labels'; folder.mkdir(exist_ok=True)
    frame.to_parquet(folder/'proposals.parquet',index=False,compression='zstd')
    frame.to_csv(folder/'proposals.csv',index=False,encoding='utf-8',lineterminator='\n')
    pins={}
    for path in sorted((args.root/'data/corpus').glob('*'))+sorted((args.root/'data/kg').glob('*')):
        if path.is_file():
            with path.open('rb') as stream: pins[path.relative_to(args.root).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
    manifest={'schema':'public_cultural_proposals_v1','rows':len(frame),'status_counts':frame.status.value_counts().to_dict(),
              'review_status':'pending','base_data_version':'v21','local_source_enrichment_version':'v22-labels.1',
              'base_payload_sha256':pins,'private_prose_published':False,
              'limitations':['Quote matching is not semantic verification.','Not ground truth; not eligible for silent benchmark cohort expansion.',
                             'Abstention means no accepted proposal under this protocol, not absence of cultural identity.',
                             'Unlisted recipe IDs were not processed; recovery may be partial.'],
              'scope_crosswalk':{'Indian':'indian','Pan-Indian':'indian','Fusion':'indo-fusion (owner dataset convention)','International':None}}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'rows':len(frame),'status_counts':manifest['status_counts']}))
if __name__=='__main__': main()
