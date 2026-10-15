"""Separate requested character pose from the pose used to reconstruct and rig it."""
import hashlib
from pathlib import Path
import re

def plan_pose(description, animation_requested=False):
    text=description.casefold().replace('_',' ').replace('-',' ')
    if re.search(r'\b(koer\w*|kass\w*|hunt\w*|hundi\w*|hobu\w*|karu\w*|dog|cat|wolf|horse|bear)\b',text):
        kind,body,rest='living','quadruped','quadruped_stand'
    elif re.search(r'\b(inime\w*|mees\w*|nais\w*|naine|sõdal\w*|sõdur\w*|viiking\w*|viking\w*|human|soldier|warrior)\b',text):
        kind,body,rest='living','humanoid','humanoid_t'
    elif re.search(r'\b(kolet\w*|tulnuk\w*|draakon\w*|lind\w*|monster|alien|dragon|bird)\b',text):
        kind,body,rest='living','custom','needs_body_plan_review'
    elif re.search(r'\b(auto\w*|ralliauto\w*|mõõk\w*|laud\w*|maja\w*|tool|car|sword|table|house|chair)\b',text):
        kind,body,rest='rigid_object','rigid','object_reference_pose'
    else:
        kind,body,rest='needs_review','unknown','needs_body_plan_review'
    # The target reference remains authoritative for poses not covered by these aliases.
    target='reference_defined'
    for pattern,value in [(r'\bsits\w*\b','sit_pretty'),(r'\bistu\w*\b','sit'),(r'\bjooks\w*\b|\brunning\b','run'),(r'\bhüpp\w*\b|\bjumping\b','jump'),(r'\bseis\w*\b|\bstanding\b','stand')]:
        if re.search(pattern,text):target=value;break
    explicit_target=target!='reference_defined'
    living=kind=='living'
    requires_rig=living
    return {
        'subject_kind':kind,'body_plan':body,'reconstruction_pose':rest,
        'requested_pose_description':description,'target_pose_kind':target,
        'requested_pose_reference_role':'identity_appearance_and_final_pose',
        'four_view_reference_role':'same_identity_in_reconstruction_pose',
        'neutral_reference_required':living,
        'requires_rig':requires_rig,
        'requires_anatomy_review':body in ('custom','unknown'),
        'target_pose_created_by':'armature_deformation' if requires_rig else 'not_requested',
        'animation_required':requires_rig,
        'animation_steps':['rest_pose','transition_to_requested_pose','hold_requested_pose'] if requires_rig else [],
        'canonical_pose_guidance':{
            'humanoid_t':'Upright T pose, arms extended, fingers separated, feet apart; no crossed or occluded limbs.',
            'quadruped_stand':'Standing naturally on all four feet, straight trunk, visible limb separation, relaxed head and tail; no seated or folded legs.',
            'needs_body_plan_review':'Establish limb count, joint chains and an unoccluded neutral pose from the reference before reconstruction.',
            'object_reference_pose':'Preserve the object pose and mechanically meaningful separate parts.'
        }[rest],
        'checks':['same_identity_across_references','same_neutral_pose_in_four_views','visible_or_anatomically_inferred_joints','organic_cross_section_depth','joint_edge_flow','skin_weights','self_intersection_in_target_pose','stance_contacts_in_target_pose','final_pose_against_requested_reference'] if living else ['reference_consistency','surface_integrity']
    }

def validate_reference_manifest(request, manifest, input_path):
    """Verify provenance and a recorded visual review; this does not inspect pixels."""
    pose=request.get('pose_plan')
    if request.get('schema_version',0)<2 or not isinstance(pose,dict) or 'subject_kind' not in pose:
        raise ValueError('Tellimus vajab uut poosiplaani; koosta request.json praeguse command.py abil.')
    if pose.get('requires_anatomy_review'):
        raise ValueError('Selle olendi kehaehitus ja ehituspoos vajavad enne rekonstruktsiooni eraldi ülevaatust.')
    if not pose.get('neutral_reference_required'):
        return {'neutral_pose_required':False,'visual_pose_verified_by_code':False}
    expected=pose['reconstruction_pose']
    if manifest.get('reference_role')!='rest_pose' or manifest.get('rest_pose')!=expected:
        raise ValueError(f'Nelivaade peab olema ehituspoosis {expected}; tellitud lõpp-poosi pilti ei tohi kasutada selle asemel.')
    if manifest.get('body_plan')!=pose['body_plan']:
        raise ValueError('Nelivaate kehaehitus ei vasta tellimuse luustikuplaanile.')
    if set(manifest.get('views',[]))!={'front','left','back','right'} or len(manifest.get('views',[]))!=4:
        raise ValueError('Vaja on nelja joondatud vaadet: front, left, back, right.')
    for field in ('same_identity','same_pose','registered_scale','limbs_separated'):
        if manifest.get(field) is not True:raise ValueError(f'Nelivaate visuaalkontroll on puudulik: {field}.')
    review=manifest.get('visual_review',{})
    if review.get('status')!='approved' or not review.get('reviewer'):
        raise ValueError('Ehituspoosi nelivaade vajab dokumenteeritud visuaalset ülevaatust.')
    digest=hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
    if manifest.get('source_input_sha256')!=digest:
        raise ValueError('Poosikontrolli manifest ei kuulu sellele nelivaate andmefailile.')
    return {'neutral_pose_required':True,'reconstruction_pose':expected,'input_sha256':digest,'visual_review':review,'visual_pose_verified_by_code':False}
