"""Round ambiguous organic cross sections while preserving source silhouettes.

This is a shape prior, not measured depth. Split mask intervals keep separated
limbs separate; skeleton-guided regional depth is still needed for detailed rigs.
"""
import numpy as np

def intervals(mask,axis):
    indices=np.flatnonzero(mask)
    if not len(indices):return []
    chunks=np.split(indices,np.flatnonzero(np.diff(indices)>1)+1)
    halfstep=abs(float(axis[1]-axis[0]))*.5
    return [((float(axis[c[0]])+float(axis[c[-1]]))/2,max((float(axis[c[-1]])-float(axis[c[0]]))/2+halfstep,halfstep)) for c in chunks]

def round_organic_sections(phi,x,y,z,front_mask,back_mask,left_mask,right_mask):
    rounded=phi.copy()
    fm=(front_mask&back_mask)[::-1];sm=(left_mask&right_mask)[::-1]
    for k in range(len(z)):
        xs=intervals(fm[k],x);ys=intervals(sm[k],y)
        if not xs or not ys:continue
        prior=np.full((len(x),len(y)),-np.inf)
        for cx,rx in xs:
            for cy,ry in ys:
                ellipse=(1-np.sqrt(((x[:,None]-cx)/rx)**2+((y[None,:]-cy)/ry)**2))*min(rx,ry)
                prior=np.maximum(prior,ellipse)
        rounded[:,:,k]=np.minimum(rounded[:,:,k],prior)
    return rounded
