"""Location preference from explicitly published places only; never infers office addresses."""
BLEKINGE={'karlskrona','karlshamn','ronneby','sölvesborg','olofström','nättraby','blekinge'}

def in_blekinge(locations):
    return any(p.casefold().strip() in BLEKINGE for p in locations)

def regional_alignment(a,b):
    left={p.casefold().strip() for p in a.directory_profile.get('locations',[])}
    right={p.casefold().strip() for p in b.directory_profile.get('locations',[])}
    if left&right:return 2
    return 1 if in_blekinge(left) and in_blekinge(right) else 0
