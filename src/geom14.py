import numpy as np, trimesh
from shapely.geometry import box as sbox, Polygon

# ---- pick data (measured) ----
pick_length, grip_w, tip_w, pick_t = 48.0, 10.0, 3.0, 2.0

# ---- cavity ----
int_w, int_l_set, int_h = 48.0, 61.0, 20.0

# ---- shell ----
wall, floor_t, lid_t, lip = 4.0, 2.8, 2.35, 1.6
rail, clr = 1.6, 0.25
corner_r = 10.0                      # squircle footprint
int_r = corner_r - wall              # cavity offset inward -> constant wall
flange_r = int_r + rail              # lid flange offset outward from the cavity
top_ch, bot_ch = 1.6, 0.0            # square base: full footprint on the plate
plinth_z, plinth_h, plinth_d = 2.0, 1.2, 0.5   # shadow groove, clear of layer 1
gap = 0.35                           # shadow gap around the flush panel
flute_r, flute_d, flute_pitch = 0.9, 0.45, 3.4
swale_a, swale_b, swale_d = 7.0, 4.5, 1.0
# Catch and spring. Two things changed after the v13 print dropped filament
# into the slot.
#
# 1. Every Z face now lands on the 0.20 layer grid. v13 put the strip underside
#    at 107.5 layers, so the slicer had to round the bridge to 107 or 108 and
#    the strip came out 1.2 or 1.4 rather than 1.3 — a 25% swing in catch force
#    and an ambiguous start for a 32.6 mm bridge.
#      strip underside  22.8 - 1.2 = 21.6 = layer 108
#      slot floor       21.6 - 2.4 = 19.2 = layer  96
#      ridge crest      22.8 + 1.0 = 23.8 = layer 119
#
# 2. The slot is 2.4 rather than 1.5. The 32.6 mm bridge is forced by the
#    topology — the strip is a ribbon suspended at its two ends, and its length
#    is what makes the spring soft (k goes as 1/span^3, so a shorter strip is
#    not available). The slot cannot stop the bridge sagging, so instead it is
#    deep enough that sag cannot reach the floor and weld the strip solid.
#
# relief_r grows with the slot. The circles have to project past the slot to
# root the strip in a radius; at the old 1.3 a 2.4 slot left only 0.10 mm of
# projection, i.e. the square corner v9 added these holes to avoid. 1.8 keeps
# the v13 proportion (+0.60 mm) at a 3.6 diameter, nine line widths.
#
# The longer relief lengthens the span 32.6 -> 33.6, so the catch softens to
# 2.92 N. That sits in the band v10 tuned to (2.8 N), and engagement is deeper
# than v13 at 0.50 mm, so the click is more positive despite the lower peak.
det_h, det_r = 1.0, 1.9              # click ridge
tongue_w, tongue_t, slot_h = 30.0, 1.2, 2.4   # sprung strip carrying it
relief_r, slot_ch = 1.8, 0.4         # stress-relief ends + edge chamfers
scoop_d, scoop_r = 1.2, 9.0
floor_fillet = 2.0                   # radius where the floor meets the walls

int_l = int_l_set
out_l = int_l + 2*wall
out_w = int_w + 2*wall
lid_z = floor_t + int_h + clr
out_h = lid_z + lid_t + lip
shelf_z = lid_z - clr
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
    a = lid_solid(clr)
    b = lid_solid(clr); b.apply_translation([0, out_l + 25, 0])
    return trimesh.util.concatenate([a, b]).convex_hull

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

def detent_ridge():
    cyl = trimesh.creation.cylinder(radius=det_r, height=tongue_w, sections=64)
    cyl.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    cyl.apply_translation([0, y_end, shelf_z - det_r + det_h])
    clip = trimesh.creation.box(extents=[tongue_w, wall, det_h + 0.02])
    clip.apply_translation([0, y_end, shelf_z + det_h/2])
    return trimesh.boolean.intersection([cyl, clip], engine='manifold')

def _xz_prism(poly, y0, y1):
    """Extrude a 2-D profile given in (x, z) along Y from y0 to y1."""
    m = trimesh.creation.extrude_polygon(poly, y1 - y0)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
    m.apply_translation([0, y1, 0])
    return m

def _slot_parts():
    """Convex pieces of the slot profile: the stadium plus a relief circle
    at each end, so the strip roots into a radius, not a square corner."""
    zc = shelf_z - tongue_t - slot_h/2
    from shapely.geometry import Point
    stad = sbox(-tongue_w/2, zc - slot_h/2, tongue_w/2, zc + slot_h/2)
    parts = [stad]
    for sx in (-1, 1):
        parts.append(Point(sx * tongue_w/2, zc).buffer(relief_r, resolution=24))
    return parts

def spring_slot():
    """Slot with radiused ends and chamfered lips inside and out."""
    ya, yb = y_end - wall/2, y_end + wall/2
    solids = []
    for p in _slot_parts():
        solids.append(_xz_prism(p, ya - 1.0, yb + 1.0))
        big = p.buffer(slot_ch, resolution=16)
        for face, sgn in ((ya, -1), (yb, 1)):
            near = _xz_prism(big, face + sgn*0.005, face + sgn*0.01)
            far = _xz_prism(p, face - sgn*slot_ch, face - sgn*slot_ch + 0.005)
            solids.append(trimesh.util.concatenate([near, far]).convex_hull)
    return trimesh.boolean.union(solids, engine='manifold')

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
    cav = cavity()
    case = trimesh.boolean.difference(
        [outer_shell(), cav, channel(), flutes(), plinth_groove(), spring_slot()],
        engine='manifold')
    return trimesh.boolean.union([case, detent_ridge()], engine='manifold')

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
