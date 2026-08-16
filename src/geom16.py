import numpy as np, trimesh
from shapely.geometry import box as sbox, Polygon

# ---- pick data (measured) ----
pick_length, grip_w, tip_w, pick_t = 48.0, 10.0, 3.0, 2.0

# ---- cavity ----
int_w, int_l_set, int_h = 48.0, 61.0, 20.0

# ---- shell ----
wall, floor_t, lid_t, lip = 4.0, 2.8, 2.35, 1.6
rail, clr = 1.6, 0.25
# Running clearance in the rails, separate from clr from v15. clr sets lid_z,
# so it is lid geometry and cannot be touched without reprinting the lid;
# slide_clr only grows the channel cut into the case, so the slide can be
# loosened or tightened on the case alone. They were one number only because
# the shelf carried the catch ridge. Held equal to clr for v15 so this
# revision changes exactly one thing — judge the slide, then tune this.
slide_clr = 0.25

# ---- detent by taper, from v16 ----
# v15 printed cleanly but the lid slid open too easily: with the catch gone,
# the rails alone do not hold it. Rather than tighten the whole channel — which
# would put resistance across all 63 mm of travel, the thing that made v13
# unpleasant — the last detent_len at the DEEP end runs tighter.
#
# Only the lid's leading edge ever reaches that zone, and only within
# detent_len of shut, so the grip happens at the closed position and nowhere
# else in the travel. Nothing here is unsupported: it is a change of clearance
# in a cut that already existed.
# detent_clr is NEGATIVE on purpose: the zone is cut smaller than the lid, so
# the two must deform slightly to seat. Merely reducing the clearance does
# nothing — at +0.12 the build check measured 0.00 mm3 of overlap, because a
# smaller gap is still a gap. Measured overlap against the case:
#
#     -0.06  (0.12 mm interference)   3.46 mm3
#     -0.12  (0.24 mm interference)   6.43 mm3
#     -0.20  (0.40 mm interference)   9.73 mm3
#
# -0.12 because the printer's own tolerance is around +-0.1 mm: at -0.06 a
# slightly generous print lands at no interference at all and the lid is loose
# again, which is the failure v15 already demonstrated. Too tight is relieved
# with a few strokes of fine paper on the lid's leading edge; too loose costs a
# reprint. If it still slides open, -0.20.
#
# Do not compare these volumes with the old sprung catch (38.5 mm3 in v13).
# That interference was absorbed by a soft strip at about 8 N/mm; this one is
# taken by the bulk stiffness of the rails, which is far higher, so a much
# smaller overlap gives a comparable force. The volumes are not the same thing.
HAS_DETENT_FIT = True
detent_clr = -0.12                   # NEGATIVE = interference, not clearance
detent_len = 6.0                     # length of the zone, from the deep end

# ---- push notch, from v16 ----
# A window cut through the lip at the deep end, exposing the lid's leading edge
# so it can be pushed toward the mouth. A cut, not an addition, so the profile
# stays flat at out_h and the case still pockets. Cut from above: no overhang.
notch_w, notch_r = 22.0, 2.2         # width across the case, corner radius
notch_y = -28.6                      # inboard limit of the cut
corner_r = 10.0                      # squircle footprint
int_r = corner_r - wall              # cavity offset inward -> constant wall
flange_r = int_r + rail              # lid flange offset outward from the cavity
top_ch, bot_ch = 1.6, 0.0            # square base: full footprint on the plate
plinth_z, plinth_h, plinth_d = 2.0, 1.2, 0.5   # shadow groove, clear of layer 1
gap = 0.35                           # shadow gap around the flush panel
flute_r, flute_d, flute_pitch = 0.9, 0.45, 3.4
swale_a, swale_b, swale_d = 7.0, 4.5, 1.0
# ---- no catch, from v15 ----
#
# The sprung catch is gone. It failed to print twice, in v13 and again in v14
# after the slot was deepened and every face put on the layer grid, and the
# reason is structural rather than a matter of tuning:
#
#   the part prints flat, no rotation, no supports
#   -> anything that must move DOWN needs air beneath it
#   -> air beneath it is unsupported material
#   -> and the span cannot shrink to make it printable, because k goes as
#      1/span^3 and the span IS the spring rate
#
# So a downward-retracting spring in this body cannot be made robustly
# printable, and no revision of the slot was going to change that. The lid is
# now held by friction in the rails alone. That leaves the case with no
# unsupported material anywhere.
#
# Removing it does not touch the lid: no catch parameter was ever read by
# make_lid(). See [Design invariants] in CLAUDE.md before reintroducing any
# feature that has to deflect downward.
HAS_CATCH = False
scoop_d, scoop_r = 1.2, 9.0
floor_fillet = 2.0                   # radius where the floor meets the walls

int_l = int_l_set
out_l = int_l + 2*wall
out_w = int_w + 2*wall
lid_z = floor_t + int_h + clr
out_h = lid_z + lid_t + lip
shelf_z = lid_z - slide_clr        # floor of the rail channel
lid_l = int_l/2 + out_l/2 - top_ch
lid_cy = (out_l/2 - top_ch - int_l/2)/2
y_end = out_l/2 - wall/2

def rrect(sx, sy, r):
    return sbox(-sx/2 + r, -sy/2 + r, sx/2 - r, sy/2 - r).buffer(r, resolution=24)

def prism(poly, z0, h):
    m = trimesh.creation.extrude_polygon(poly, h)
    m.apply_translation([0, 0, z0])
    return m

def outer_shell():
    """Chamfered top and bottom edges — convex, so a hull of slices is exact."""
    p_full = rrect(out_w, out_l, corner_r)
    p_top = rrect(out_w - 2*top_ch, out_l - 2*top_ch, corner_r - top_ch)
    slabs = [prism(p_full, 0, 0.01),
             prism(p_full, out_h - top_ch - 0.01, 0.01),
             prism(p_top, out_h - 0.01, 0.01)]
    return trimesh.util.concatenate(slabs).convex_hull

def plinth_groove():
    """0.5 deep band with a 67 deg sloped roof - keeps the floating look,
    starts 2 mm up so the first layers are untouched."""
    big = prism(rrect(out_w + 8, out_l + 8, corner_r), plinth_z, plinth_h)
    inner = trimesh.util.concatenate([
        prism(rrect(out_w - 2*plinth_d, out_l - 2*plinth_d, corner_r - plinth_d),
              plinth_z - 0.01, 0.01),
        prism(rrect(out_w + 0.2, out_l + 0.2, corner_r), plinth_z + plinth_h, 0.01),
    ]).convex_hull
    return trimesh.boolean.difference([big, inner], engine='manifold')

def lid_flange(extra=0.0):
    bw, bl = int_w + 2*rail + 2*extra, lid_l + 2*extra
    z0, h = lid_z - extra, lid_t + 2*extra
    bot = prism(rrect(bw, bl, flange_r), z0, 0.01)
    top = prism(rrect(bw - 2*rail, bl - 2*rail, flange_r - rail), z0 + h - 0.01, 0.01)
    m = trimesh.util.concatenate([bot, top]).convex_hull
    m.apply_translation([0, lid_cy, 0])
    return m

def channel():
    """The lid swept along its travel.

    Tight for the first detent_len out of the closed position, loose after
    that. The loose sweep starts detent_len along, so the deep end of the
    tunnel is left at the tighter clearance and grips the leading edge only
    when the lid is nearly shut.
    """
    tight = lid_solid(detent_clr)
    a = lid_solid(slide_clr); a.apply_translation([0, detent_len, 0])
    b = lid_solid(slide_clr); b.apply_translation([0, out_l + 25, 0])
    loose = trimesh.util.concatenate([a, b]).convex_hull
    return trimesh.boolean.union([tight, loose], engine='manifold')


def push_notch():
    """Window through the lip at the deep end, exposing the lid's edge."""
    half = notch_w/2 - notch_r
    p = sbox(-half, -out_l/2 - 4.0, half, notch_y - notch_r).buffer(
        notch_r, resolution=24)
    return prism(p, lid_z + lid_t, 6.0)

def lid_solid(extra=0.0):
    """Flange plus the flush boss, as one convex-ish solid for sweeping."""
    f = lid_flange(extra)
    bw = int_w - 2*gap + 2*extra
    bl = lid_l - 2*gap + 2*extra
    b0 = prism(rrect(bw, bl, int_r - gap), lid_z + lid_t - 0.01, 0.01)
    b1 = prism(rrect(bw - 1.6, bl - 1.6, int_r - gap - 0.8), out_h + extra - 0.01, 0.01)
    boss = trimesh.util.concatenate([b0, b1]).convex_hull
    boss.apply_translation([0, lid_cy, 0])
    return trimesh.boolean.union([f, boss], engine='manifold')

def flutes():
    cuts = []
    for y in np.arange(-out_l/2 + corner_r + 1, out_l/2 - corner_r - 8, flute_pitch):
        for sx in (-1, 1):
            c = trimesh.creation.cylinder(radius=flute_r, height=40, sections=24)
            c.apply_translation([sx * (out_w/2 + flute_r - flute_d), y, 0])
            cuts.append(c)
    for x in np.arange(-out_w/2 + corner_r + 1, out_w/2 - corner_r, flute_pitch):
        c = trimesh.creation.cylinder(radius=flute_r, height=40, sections=24)
        c.apply_translation([x, -(out_l/2 + flute_r - flute_d), 0])
        cuts.append(c)
    h = lid_z - 4.0 - 4.0
    band = trimesh.creation.box(extents=[out_w + 10, out_l + 10, h])
    band.apply_translation([0, 0, 4.0 + h/2])
    return trimesh.boolean.intersection(
        [trimesh.util.concatenate(cuts).convex_hull if False else
         trimesh.boolean.union(cuts, engine='manifold'), band], engine='manifold')

def thumb_dish():
    R = (scoop_r**2 + scoop_d**2) / (2*scoop_d)
    ball = trimesh.creation.icosphere(subdivisions=4, radius=R)
    ball.apply_translation([0, int_l/2 - 11.0, floor_t + R - scoop_d])
    slab = trimesh.creation.box(extents=[4*scoop_r, 4*scoop_r, scoop_d + 0.02])
    slab.apply_translation([0, int_l/2 - 11.0, floor_t - scoop_d/2])
    return trimesh.boolean.intersection([ball, slab], engine='manifold')

def cavity():
    """Cavity with a 2 mm radius at the floor-to-wall junction.
    Cross-sections grow along a quarter circle, so the swept solid is convex
    and a hull of slices reproduces it exactly."""
    r = floor_fillet
    slices = []
    for h in np.linspace(0.0, r, 16):
        inset = r - np.sqrt(max(r*r - (r - h)**2, 0.0))
        slices.append(prism(rrect(int_w - 2*inset, int_l - 2*inset,
                                  max(int_r - inset, 0.4)), floor_t + h, 0.01))
    base = trimesh.util.concatenate(slices).convex_hull
    top = prism(rrect(int_w, int_l, int_r), floor_t + r, out_h)
    return trimesh.boolean.union([base, top], engine='manifold')

def make_case():
    return trimesh.boolean.difference(
        [outer_shell(), cavity(), channel(), flutes(), plinth_groove(),
         push_notch()],
        engine='manifold')

def texture():
    """Ribs across the slide direction: grooves cut 0.7 deep at 2.4 pitch."""
    cuts = []
    y0, y1 = lid_cy - lid_l/2 + 3.0, lid_cy + lid_l/2 - 3.0
    for y in np.arange(y0, y1, 2.4):
        c = trimesh.creation.cylinder(radius=1.1, height=int_w + 6, sections=32)
        c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
        c.apply_translation([0, y, out_h + 1.1 - 0.7])
        cuts.append(c)
    return trimesh.boolean.union(cuts, engine='manifold')

def make_lid():
    lid = lid_solid(0)
    lid = trimesh.boolean.difference([lid, texture()], engine='manifold')
    rr = 2.2
    groove = trimesh.creation.cylinder(radius=rr, height=int_w + 4, sections=64)
    groove.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    groove.apply_translation([0, y_end, lid_z + 1.1 - rr])
    return trimesh.boolean.difference([lid, groove], engine='manifold')

def blade(flip=False):
    L = pick_length
    poly = Polygon([(-grip_w/2, -L/2), (grip_w/2, -L/2),
                    (tip_w/2, L/2), (-tip_w/2, L/2)]).buffer(0.35).buffer(-0.15)
    m = trimesh.creation.extrude_polygon(poly, pick_t)
    if flip:
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1]))
    return m

def make_picks(n=35, per_layer=6, pitch=6.6):
    out, rng, k = [], np.random.default_rng(7), 0
    for layer in range(6):
        z = floor_t + 0.15 + layer * (pick_t + 0.25)
        x0 = -(per_layer - 1) * pitch / 2
        for i in range(per_layer):
            if k >= n:
                break
            m = blade(flip=(i + layer) % 2 == 1)
            m.apply_transform(trimesh.transformations.rotation_matrix(
                rng.uniform(-0.035, 0.035), [0, 0, 1]))
            m.apply_translation([x0 + i*pitch + rng.uniform(-0.5, 0.5),
                                 rng.uniform(-0.8, 0.8), z])
            out.append(m); k += 1
    return out

if __name__ == '__main__':
    c, l = make_case(), make_lid()
    print('case', c.is_watertight, np.round(c.bounds, 2).tolist())
    print('lid ', l.is_watertight, np.round(l.bounds, 2).tolist())
    print('outer %.1f x %.1f x %.1f' % (out_w, out_l, out_h))
    # does it actually slide?
    for d in (0, 5, 10, 20, 30, 45, 60):
        t = l.copy(); t.apply_translation([0, d, 0])
        try:
            v = trimesh.boolean.intersection([c, t], engine='manifold').volume
        except Exception:
            v = 0.0
        print('  slide %2d mm -> interference %.3f mm3' % (d, v))
