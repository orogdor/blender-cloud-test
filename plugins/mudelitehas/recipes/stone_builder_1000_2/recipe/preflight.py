#!/usr/bin/env python3
"""Mandatory fail-closed review and source hashes; cannot visually verify pictures."""
import argparse
from pathlib import Path
from common import read_inputs,write_json

def main():
    a=argparse.ArgumentParser();a.add_argument('--manifest',type=Path,required=True)
    a.add_argument('--output',type=Path,required=True);a.add_argument('--allow-synthetic-test',action='store_true');o=a.parse_args()
    d=read_inputs(o.manifest,allow_synthetic=o.allow_synthetic_test)
    report={'recipe':'stone-builder-1000-2','status':'registered_not_reconstructed',
            'source_hashes':d['hashes'],'view_order':d['views'],'independent_axes':3,
            'registration_verified_by_code':True,'visual_review_verified_by_code':False,
            'reviewer_attestation':d['manifest']['visual_review'],'synthetic_test':d['synthetic_test'],
            'warnings':['Reviewer statements are declarations; image identity and pose cannot be established from JSON alone.',
                        'Projection registration uses assumed orthographic camera parameters.']}
    write_json(o.output,report);print('PRE-FLIGHT OK:',', '.join(d['views']))
if __name__=='__main__':main()
